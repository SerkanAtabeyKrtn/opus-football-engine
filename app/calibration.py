"""Small, deterministic ridge multinomial calibration; fit only on past data."""
import numpy as np


def softmax(logits):
    z = logits - np.max(logits, axis=1, keepdims=True)
    e = np.exp(z)
    return e / np.sum(e, axis=1, keepdims=True)


def fit(features, labels, classes, penalty=30.0):
    x = np.asarray(features, dtype=float)
    y = np.asarray(labels, dtype=int)
    if len(x) < 100 or not np.isfinite(x).all() or set(y) != set(range(classes)):
        raise ValueError('Kalibrasyon için yeterli ve geçerli eğitim verisi yok')
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale < 1e-8] = 1.0
    x = np.column_stack([np.ones(len(x)), (x - mean) / scale])
    n, d = x.shape
    k = classes - 1
    w = np.zeros((k, d))
    target = np.eye(classes)[y]
    regularizer = np.full(d, float(penalty))
    regularizer[0] = 0.01

    def objective(weights):
        probs = softmax(np.column_stack([x @ weights.T, np.zeros(n)]))
        loss = -np.log(np.clip(probs[np.arange(n), y], 1e-12, 1)).sum()
        return loss + 0.5 * np.sum(weights * weights * regularizer), probs

    converged = False
    for iteration in range(60):
        loss, p = objective(w)
        gradient = (p[:, :k] - target[:, :k]).T @ x + w * regularizer
        hessian = np.zeros((k * d, k * d))
        for a in range(k):
            for b in range(k):
                weights = p[:, a] * ((1.0 if a == b else 0.0) - p[:, b])
                block = x.T @ (x * weights[:, None])
                if a == b:
                    block += np.diag(regularizer)
                hessian[a*d:(a+1)*d, b*d:(b+1)*d] = block
        step = np.linalg.solve(hessian, gradient.ravel()).reshape(k, d)
        rate = 1.0
        while rate > 1e-6 and objective(w - rate * step)[0] > loss:
            rate *= 0.5
        w -= rate * step
        if np.max(np.abs(rate * step)) < 1e-7:
            converged = True
            break
    if not converged or not np.isfinite(w).all():
        raise ValueError('Kalibrasyon çözücüsü yakınsamadı; yeni model kullanılmadı')
    return {'mean': mean.tolist(), 'scale': scale.tolist(), 'weights': w.tolist(),
            'classes': classes, 'penalty': penalty, 'iterations': iteration + 1,
            'trainingCount': n}


def predict(model, features):
    if not features:
        return []
    x = np.asarray(features, dtype=float)
    x = np.column_stack([np.ones(len(x)), (x - model['mean']) / model['scale']])
    w = np.asarray(model['weights'])
    return softmax(np.column_stack([x @ w.T, np.zeros(len(x))])).tolist()


def metrics(probabilities, labels):
    if not probabilities:
        return {'n': 0, 'brier': None, 'logLoss': None, 'accuracy': None}
    p = np.asarray(probabilities)
    y = np.asarray(labels, dtype=int)
    target = np.eye(p.shape[1])[y]
    return {'n': len(y), 'brier': float(np.mean((p - target)**2)),
            'logLoss': float(-np.log(np.clip(p[np.arange(len(y)), y], 1e-12, 1)).mean()),
            'accuracy': float((p.argmax(axis=1) == y).mean())}
