import math


class OneEuroFilter:
    def __init__(self, t0: float, x0: tuple[float, float], min_cutoff: float = 1.0, beta: float = 0.02, d_cutoff: float = 1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_prev = x0
        self.dx_prev = (0.0, 0.0)
        self.t_prev = t0

    def __call__(self, t: float, x: tuple[float, float]) -> tuple[float, float]:
        te = t - self.t_prev
        if te <= 0.0:
            return x
            
        # 1. Compute velocity
        adiff = (x[0] - self.x_prev[0], x[1] - self.x_prev[1])
        dx = (adiff[0] / te, adiff[1] / te)
        
        # 2. Smooth velocity
        alpha_d = self._alpha(te, self.d_cutoff)
        dx_hat = (
            dx[0] * alpha_d + self.dx_prev[0] * (1.0 - alpha_d),
            dx[1] * alpha_d + self.dx_prev[1] * (1.0 - alpha_d)
        )
        
        # 3. Compute cutoff from smoothed velocity
        cutoff = (
            self.min_cutoff + self.beta * abs(dx_hat[0]),
            self.min_cutoff + self.beta * abs(dx_hat[1])
        )
        
        # 4. Smooth position
        alpha_x = (
            self._alpha(te, cutoff[0]),
            self._alpha(te, cutoff[1])
        )
        x_hat = (
            x[0] * alpha_x[0] + self.x_prev[0] * (1.0 - alpha_x[0]),
            x[1] * alpha_x[1] + self.x_prev[1] * (1.0 - alpha_x[1])
        )
        
        # 5. Store state
        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t
        
        return x_hat
        
    def _alpha(self, te: float, cutoff: float) -> float:
        tau = 1.0 / (2 * math.pi * cutoff)
        return te / (te + tau)
