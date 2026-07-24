"""Phase 2 — the Dixon-Coles goals engine (statistical core).

Classic Dixon-Coles (1997) bivariate-Poisson model with a low-score correlation
correction and exponential time-decay weighting. Each team gets an attack and a
defence rating; a shared home-advantage term and a correlation term rho complete
the model. Fitted by weighted maximum likelihood.

    log lambda_home = home_adv + attack[home] + defence[away]
    log mu_away     =           attack[away] + defence[home]

Higher `attack` => scores more; higher `defence` => concedes more (weaker).

From a fitted model we build the full scoreline probability matrix for any
fixture and read off Over/Under 2.5, BTTS and 1X2 probabilities from it.

xG note (per plan): this MVP fits on actual goals. The engine is structured so
the goal inputs can later be swapped for, or blended with, xG (Understat) — see
`fit()`'s `home_goals_col`/`away_goals_col` hooks. That is a Phase 2b/4
enhancement; the goals-based core is fully functional on its own.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

# Small ridge on attack/defence ratings: resolves the attack/defence additive
# indeterminacy and shrinks thin-sample teams toward league average (desirable
# early-season regularization).
_RIDGE = 1e-3
_RHO_BOUNDS = (-0.25, 0.25)


def _tau(x, y, lam, mu, rho):
    """Dixon-Coles low-score correction, vectorized over matches."""
    out = np.ones_like(lam, dtype=float)
    m00 = (x == 0) & (y == 0)
    m01 = (x == 0) & (y == 1)
    m10 = (x == 1) & (y == 0)
    m11 = (x == 1) & (y == 1)
    out[m00] = 1.0 - lam[m00] * mu[m00] * rho
    out[m01] = 1.0 + lam[m01] * rho
    out[m10] = 1.0 + mu[m10] * rho
    out[m11] = 1.0 - rho
    return out


@dataclass
class DixonColes:
    """A Dixon-Coles model fitted to one competition's matches."""

    xi: float = 0.0018          # time-decay rate per day (~1yr half-life)
    max_goals: int = 10         # scoreline matrix truncation

    teams: list[str] = field(default_factory=list, repr=False)
    attack: dict[str, float] = field(default_factory=dict, repr=False)
    defence: dict[str, float] = field(default_factory=dict, repr=False)
    home_adv: float = 0.0
    rho: float = 0.0
    n_matches: int = 0
    ref_date: pd.Timestamp | None = None
    converged: bool = False
    blend: float = 1.0  # 1.0 = pure actual goals; 0.0 = pure xG

    # --- fitting ------------------------------------------------------------
    def fit(self, df: pd.DataFrame, ref_date=None, blend: float = 1.0) -> "DixonColes":
        """Fit on `df` (one league). Time-decay weights are relative to
        `ref_date` (defaults to the latest match date). For a backtest, pass
        only past matches and set ref_date to the fixture date.

        `blend` mixes the target that team strengths are fitted to:
            target = blend * actual_goals + (1 - blend) * xG
        blend=1.0 -> classic goals-based Dixon-Coles (integer, uses the
        low-score tau correction). blend<1.0 fits on the continuous goal/xG
        blend via the continuous Poisson MLE; the tau correction (an
        integer-score effect) is dropped and rho fixed at 0. Requires
        `home_xg`/`away_xg` columns when blend<1.0.
        """
        self.blend = blend
        use_tau = blend >= 1.0
        need = ["fthg", "ftag", "home_team", "away_team", "date"]
        if not use_tau:
            need += ["home_xg", "away_xg"]
        df = df.dropna(subset=need).copy()
        if ref_date is None:
            ref_date = df["date"].max()
        ref_date = pd.Timestamp(ref_date)
        self.ref_date = ref_date

        teams = sorted(set(df["home_team"]) | set(df["away_team"]))
        idx = {t: i for i, t in enumerate(teams)}
        n = len(teams)

        hi = df["home_team"].map(idx).to_numpy()
        ai = df["away_team"].map(idx).to_numpy()

        # Fitting targets (continuous when xG is blended in).
        gh = df["fthg"].to_numpy(dtype=float)
        ga = df["ftag"].to_numpy(dtype=float)
        if use_tau:
            th, ta = gh, ga
            xi_int, yi_int = gh.astype(int), ga.astype(int)  # for tau
        else:
            xh = df["home_xg"].to_numpy(dtype=float)
            xa = df["away_xg"].to_numpy(dtype=float)
            th = blend * gh + (1.0 - blend) * xh
            ta = blend * ga + (1.0 - blend) * xa

        age_days = (ref_date - df["date"]).dt.days.to_numpy()
        weights = np.exp(-self.xi * np.clip(age_days, 0, None))

        def neg_ll(params):
            attack = params[:n]
            defence = params[n:2 * n]
            home_adv = params[2 * n]
            rho = params[2 * n + 1]
            attack = attack - attack.mean()  # resolve additive indeterminacy

            log_lam = home_adv + attack[hi] + defence[ai]
            log_mu = attack[ai] + defence[hi]
            lam = np.exp(log_lam)
            mu = np.exp(log_mu)

            # Continuous Poisson MLE for the rate params (factorial term drops).
            ll = th * log_lam - lam + ta * log_mu - mu
            if use_tau:
                tau = np.clip(_tau(xi_int, yi_int, lam, mu, rho), 1e-10, None)
                ll = ll + np.log(tau)
            penalty = _RIDGE * (np.sum(attack ** 2) + np.sum(defence ** 2))
            return -np.sum(weights * ll) + penalty

        rho0 = -0.05 if use_tau else 0.0
        p0 = np.concatenate([np.zeros(n), np.zeros(n), [0.25], [rho0]])
        rho_bounds = _RHO_BOUNDS if use_tau else (0.0, 0.0)  # freeze rho for xG fits
        bounds = [(None, None)] * (2 * n) + [(None, None), rho_bounds]
        res = minimize(neg_ll, p0, method="L-BFGS-B", bounds=bounds)

        attack = res.x[:n] - res.x[:n].mean()
        defence = res.x[n:2 * n]
        self.teams = teams
        self.attack = dict(zip(teams, attack))
        self.defence = dict(zip(teams, defence))
        self.home_adv = float(res.x[2 * n])
        self.rho = float(res.x[2 * n + 1])
        self.n_matches = len(df)
        self.converged = bool(res.success)
        return self

    # --- prediction ---------------------------------------------------------
    def expected_goals(self, home: str, away: str) -> tuple[float, float]:
        lam = np.exp(self.home_adv + self.attack[home] + self.defence[away])
        mu = np.exp(self.attack[away] + self.defence[home])
        return float(lam), float(mu)

    def score_matrix(self, home: str, away: str) -> np.ndarray:
        """P(home=i, away=j) for i,j in 0..max_goals, normalized to sum 1."""
        lam, mu = self.expected_goals(home, away)
        k = np.arange(self.max_goals + 1)
        ph = poisson.pmf(k, lam)
        pa = poisson.pmf(k, mu)
        mat = np.outer(ph, pa)
        # Apply the low-score correction to the 2x2 block.
        mat[0, 0] *= 1.0 - lam * mu * self.rho
        mat[0, 1] *= 1.0 + lam * self.rho
        mat[1, 0] *= 1.0 + mu * self.rho
        mat[1, 1] *= 1.0 - self.rho
        mat = np.clip(mat, 0, None)
        return mat / mat.sum()

    def predict_markets(self, home: str, away: str) -> dict:
        """Model probabilities for the markets we bet (Phase 3 consumes this)."""
        if home not in self.attack or away not in self.attack:
            raise KeyError(f"Unknown team(s): {home!r} / {away!r} not in fitted model")
        m = self.score_matrix(home, away)
        i = np.arange(m.shape[0])[:, None]
        j = np.arange(m.shape[1])[None, :]
        lam, mu = self.expected_goals(home, away)
        total = i + j
        return {
            "exp_home_goals": lam,
            "exp_away_goals": mu,
            "p_home": float(np.tril(m, -1).sum()),   # i > j
            "p_draw": float(np.trace(m)),            # i == j
            "p_away": float(np.triu(m, 1).sum()),    # i < j
            "p_over25": float(m[total > 2.5].sum()),
            "p_under25": float(m[total < 2.5].sum()),
            "p_btts_yes": float(m[1:, 1:].sum()),
            "p_btts_no": float(m[0, :].sum() + m[:, 0].sum() - m[0, 0]),
        }

    def ratings_table(self) -> pd.DataFrame:
        """Team ratings, sorted by net strength (attack - defence)."""
        rows = [{"team": t, "attack": self.attack[t], "defence": self.defence[t],
                 "net": self.attack[t] - self.defence[t]} for t in self.teams]
        return (pd.DataFrame(rows).sort_values("net", ascending=False)
                .reset_index(drop=True))
