"""Selected historical three-entry gather encoding, not a projector builder."""
import numpy as np


def barycentric_triplets(active_projector: np.ndarray, tolerance: float = 1e-13):
    """Encode the exact FEM projector as three gather indices and weights."""
    matrix = np.asarray(active_projector, np.float64)
    indices = np.zeros((matrix.shape[0], 3), np.int32)
    weights = np.zeros((matrix.shape[0], 3), np.float64)
    counts = []
    for row in range(matrix.shape[0]):
        nonzero = np.flatnonzero(np.abs(matrix[row]) > tolerance)
        if len(nonzero) == 0 or len(nonzero) > 3:
            raise RuntimeError(
                f"projector row {row} has {len(nonzero)} active entries, expected 1--3")
        indices[row, :len(nonzero)] = nonzero
        weights[row, :len(nonzero)] = matrix[row, nonzero]
        counts.append(len(nonzero))
    reconstructed = np.zeros_like(matrix)
    for column in range(3):
        np.add.at(reconstructed, (np.arange(len(matrix)), indices[:, column]),
                  weights[:, column])
    error = float(np.max(np.abs(reconstructed-matrix)))
    if error > 2e-14:
        raise RuntimeError(f"barycentric triplet reconstruction failed: {error}")
    return indices, weights, {
        "maximum_reconstruction_error": error,
        "nonzero_count_min": int(np.min(counts)),
        "nonzero_count_max": int(np.max(counts)),
    }
