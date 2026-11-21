"""Analisis de una rafaga de imagenes capturada por trigger externo."""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import cv2
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROI = (200, 50, 400, 400)
DARK_SCENE_MEAN_THRESHOLD = 8.0
BRIGHT_PIXEL_THRESHOLD = 75
BRIGHT_EXIT_THRESHOLD = 150
BRIGHT_AREA_MIN_PX = 50
DIFF_THRESHOLD = 20
MIN_CHANGED_AREA_PX = 2000
N_BACKGROUND_FRAMES = 5
TEMPORAL_CONSISTENCY_K = 2
BLUR_KERNEL = 3
MORPHO_KERNEL_SIZE = 5
MOG2_HISTORY = 15
MOG2_VAR_THRESHOLD = 12
MOG2_DETECT_SHADOWS = False
CLAHE_CLIP = 3.0
CLAHE_GRID = (8, 8)
HOUGH_DP = 1.2
HOUGH_MIN_DIST = 55
HOUGH_PARAM1 = 60
HOUGH_PARAM2_VALUES = (8, 10, 12, 14, 16)
HOUGH_MIN_RADIUS = 120
HOUGH_MAX_RADIUS = 190
PERIMETER_SAMPLES = 360
PERIMETER_PATCH = 5
PERIMETER_MIN_GAP_DEG = 30
SEARCH_START_OFFSET = 4
SEARCH_FRAME_COUNT = 10
IGNORE_ROI_Y_FROM = 320
TRAILING_COMPONENT_THRESHOLD = 30
TRAILING_COMPONENT_MIN_AREA = 40
TRAILING_COMPONENT_INNER_MARGIN = 120
TRAILING_COMPONENT_OUTER_MARGIN = 50


@dataclass
class CircleCandidate:
    cx: float
    cy: float
    radius: float
    method: str
    score: float
    support_frames: int
    source_frame: int = 0
    active_samples: int = 0
    perimeter_sum: float = 0.0


@dataclass
class SequenceAnalysisResult:
    total_frames: int
    scene: str
    mean_background: float
    first_exit_frame: Optional[int]
    exit_confidence: str
    circle_cx: Optional[float]
    circle_cy: Optional[float]
    circle_radius: Optional[float]
    circle_method: Optional[str]
    circle_support_frames: int
    angle_frame: Optional[int]
    exit_angle_deg: Optional[float]
    angle_confidence: str
    diagnostic_path: Optional[str]


def _frame_number(path: Path) -> int:
    match = re.search(r"img_(\d+)", path.name)
    return int(match.group(1)) if match else 0


def sequence_image_paths(folder: str | Path) -> list[Path]:
    return sorted(Path(folder).glob("img_*.bmp"), key=_frame_number)


def is_sequence_folder(folder: str | Path) -> bool:
    return len(sequence_image_paths(folder)) >= 2


def load_sequence(folder: str | Path) -> list[np.ndarray]:
    frames = []
    for path in sequence_image_paths(folder):
        frame = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if frame is not None:
            frames.append(frame)
    return frames


def apply_roi(frame: np.ndarray) -> np.ndarray:
    x, y, width, height = ROI
    return frame[y : y + height, x : x + width]


def _preprocess(frame: np.ndarray, dark: bool) -> np.ndarray:
    if dark:
        return cv2.GaussianBlur(frame, (BLUR_KERNEL, BLUR_KERNEL), 0)
    enhanced = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(frame)
    return cv2.GaussianBlur(enhanced, (BLUR_KERNEL, BLUR_KERNEL), 0)


def _change_mask(reference: np.ndarray, current: np.ndarray) -> tuple[np.ndarray, int]:
    difference = cv2.absdiff(reference, current)
    _, mask = cv2.threshold(difference, DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (MORPHO_KERNEL_SIZE, MORPHO_KERNEL_SIZE)
    )
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask, int(np.count_nonzero(mask))


def _changed_area(reference: np.ndarray, current: np.ndarray) -> int:
    return _change_mask(reference, current)[1]


def _first_consistent_hit(areas: list[int], threshold: int, start: int = 0) -> Optional[int]:
    candidate = None
    hits = 0
    for index, area in enumerate(areas):
        if index >= start and area >= threshold:
            candidate = index if candidate is None else candidate
            hits += 1
            if hits >= TEMPORAL_CONSISTENCY_K:
                return candidate
        else:
            candidate = None
            hits = 0
    return None


def _classify_scene(frames: list[np.ndarray]) -> tuple[str, float]:
    samples = frames[1 : 1 + 3] if len(frames) > 3 else frames
    mean_background = float(np.mean([frame.mean() for frame in samples])) if samples else 0.0
    scene = "oscura" if mean_background < DARK_SCENE_MEAN_THRESHOLD else "mixta"
    return scene, mean_background


def _build_static_background(frames: list[np.ndarray], dark: bool) -> np.ndarray:
    start = 1
    end = min(start + N_BACKGROUND_FRAMES, len(frames))
    stack = np.stack([_preprocess(frame, dark) for frame in frames[start:end]], axis=0)
    return np.median(stack, axis=0).astype(np.uint8)


def _detect_first_exit_bright_object(frames: list[np.ndarray]) -> tuple[Optional[int], list[int]]:
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (MORPHO_KERNEL_SIZE, MORPHO_KERNEL_SIZE)
    )
    noise_areas = []
    for frame in frames[1:4]:
        blurred = cv2.GaussianBlur(apply_roi(frame), (BLUR_KERNEL, BLUR_KERNEL), 0)
        _, bright = cv2.threshold(blurred, BRIGHT_EXIT_THRESHOLD, 255, cv2.THRESH_BINARY)
        bright = cv2.morphologyEx(bright, cv2.MORPH_OPEN, kernel)
        noise_areas.append(int(np.count_nonzero(bright)))

    threshold = max(BRIGHT_AREA_MIN_PX, (max(noise_areas) if noise_areas else 0) * 3)
    areas = []
    for frame in frames:
        blurred = cv2.GaussianBlur(apply_roi(frame), (BLUR_KERNEL, BLUR_KERNEL), 0)
        _, bright = cv2.threshold(blurred, BRIGHT_EXIT_THRESHOLD, 255, cv2.THRESH_BINARY)
        bright = cv2.morphologyEx(bright, cv2.MORPH_OPEN, kernel)
        bright = cv2.morphologyEx(bright, cv2.MORPH_CLOSE, kernel)
        areas.append(int(np.count_nonzero(bright)))
    return _first_consistent_hit(areas, threshold), areas


def _detect_first_exit_static_bg(frames: list[np.ndarray], dark: bool) -> tuple[Optional[int], list[int]]:
    background = _build_static_background(frames, dark)
    background_roi = apply_roi(background)
    areas = []
    for frame in frames:
        _, area = _change_mask(background_roi, apply_roi(_preprocess(frame, dark)))
        areas.append(area)
    return _first_consistent_hit(areas, MIN_CHANGED_AREA_PX), areas


def _detect_first_exit_mog2(frames: list[np.ndarray], dark: bool) -> tuple[Optional[int], list[int]]:
    bgsub = cv2.createBackgroundSubtractorMOG2(
        history=MOG2_HISTORY,
        varThreshold=MOG2_VAR_THRESHOLD,
        detectShadows=MOG2_DETECT_SHADOWS,
    )
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (MORPHO_KERNEL_SIZE, MORPHO_KERNEL_SIZE)
    )
    warmup = min(N_BACKGROUND_FRAMES, len(frames))
    for frame in frames[1 : warmup + 1]:
        bgsub.apply(apply_roi(_preprocess(frame, dark)), learningRate=0.5)

    areas = []
    hits = 0
    candidate = None
    for index, frame in enumerate(frames):
        fg = bgsub.apply(
            apply_roi(_preprocess(frame, dark)),
            learningRate=0.01 if index >= warmup else 0.3,
        )
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, kernel)
        fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel)
        area = int(np.count_nonzero(fg))
        areas.append(area)
        if index >= warmup and area >= MIN_CHANGED_AREA_PX:
            candidate = index if candidate is None else candidate
            hits += 1
            if hits >= TEMPORAL_CONSISTENCY_K:
                return candidate, areas
        elif index >= warmup:
            candidate = None
            hits = 0
    return None, areas


def _detect_first_exit_frame_diff(frames: list[np.ndarray], dark: bool) -> tuple[Optional[int], list[int]]:
    previous = apply_roi(_preprocess(frames[0], dark))
    areas = [0]
    for frame in frames[1:]:
        current = apply_roi(_preprocess(frame, dark))
        areas.append(_changed_area(previous, current))
        previous = current
    return _first_consistent_hit(areas, MIN_CHANGED_AREA_PX), areas


def detect_first_exit(frames: list[np.ndarray]) -> tuple[Optional[int], str, float, str]:
    scene, mean_background = _classify_scene(frames)
    dark = scene == "oscura"

    if dark:
        bright_hit, _ = _detect_first_exit_bright_object(frames)
        frame_hit, _ = _detect_first_exit_frame_diff(frames, dark=True)
        if bright_hit is not None and frame_hit is not None and abs(bright_hit - frame_hit) <= 8:
            return min(bright_hit, frame_hit), scene, mean_background, "ALTA"
        if bright_hit is not None:
            return bright_hit, scene, mean_background, "MEDIA (solo D)"
        if frame_hit is not None:
            return frame_hit, scene, mean_background, "BAJA (solo C)"
        return None, scene, mean_background, "NO DETECTADO"

    static_hit, _ = _detect_first_exit_static_bg(frames, dark=False)
    mog2_hit, _ = _detect_first_exit_mog2(frames, dark=False)
    frame_hit, _ = _detect_first_exit_frame_diff(frames, dark=False)
    detections = [hit for hit in (static_hit, mog2_hit, frame_hit) if hit is not None]
    if len(detections) >= 2:
        return min(detections), scene, mean_background, f"ALTA ({len(detections)}/3)"
    if len(detections) == 1:
        return detections[0], scene, mean_background, "MEDIA (1/3)"
    return None, scene, mean_background, "NO DETECTADO"


def _crop_roi(frame: np.ndarray) -> tuple[np.ndarray, int, int]:
    x, y, width, height = ROI
    return frame[y : y + height, x : x + width], x, y


def _perimeter_signal(
    frame: np.ndarray, cx: float, cy: float, radius: float
) -> tuple[np.ndarray, np.ndarray]:
    roi, offset_x, offset_y = _crop_roi(frame)
    cx_roi = cx - offset_x
    cy_roi = cy - offset_y
    _, bright = cv2.threshold(roi, BRIGHT_PIXEL_THRESHOLD, 255, cv2.THRESH_BINARY)
    height, width = bright.shape
    half = PERIMETER_PATCH // 2
    theta = np.linspace(0, 2 * np.pi, PERIMETER_SAMPLES, endpoint=False)
    signal = np.zeros(PERIMETER_SAMPLES, dtype=float)
    for index, angle in enumerate(theta):
        px = int(round(cx_roi + radius * np.cos(angle)))
        py = int(round(cy_roi + radius * np.sin(angle)))
        if py >= IGNORE_ROI_Y_FROM:
            continue
        x0, x1 = max(0, px - half), min(width, px + half + 1)
        y0, y1 = max(0, py - half), min(height, py + half + 1)
        if x1 > x0 and y1 > y0:
            signal[index] = bright[y0:y1, x0:x1].sum() / 255.0
    return theta, signal


def _unique_candidates(candidates: list[tuple]) -> list[tuple]:
    unique = []
    for candidate in candidates:
        cx, cy, radius, _, _ = candidate
        duplicate = False
        for ux, uy, ur, _, _ in unique:
            if abs(cx - ux) < 8 and abs(cy - uy) < 8 and abs(radius - ur) < 8:
                duplicate = True
                break
        if not duplicate:
            unique.append(candidate)
    return unique


def _hough_candidates(frame: np.ndarray, frame_index: int) -> list[tuple]:
    roi, offset_x, offset_y = _crop_roi(frame)
    enhanced = cv2.createCLAHE(clipLimit=CLAHE_CLIP, tileGridSize=CLAHE_GRID).apply(roi)
    blurred = cv2.GaussianBlur(enhanced, (5, 5), 2)
    candidates = []
    for param2 in HOUGH_PARAM2_VALUES:
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=HOUGH_DP,
            minDist=HOUGH_MIN_DIST,
            param1=HOUGH_PARAM1,
            param2=param2,
            minRadius=HOUGH_MIN_RADIUS,
            maxRadius=HOUGH_MAX_RADIUS,
        )
        if circles is not None:
            for cx, cy, radius in circles[0]:
                candidates.append(
                    (float(cx + offset_x), float(cy + offset_y), float(radius),
                     f"hough_p2_{param2}", frame_index)
                )
    return _unique_candidates(candidates)


def _fit_circle_lstsq(points: np.ndarray) -> Optional[tuple[float, float, float]]:
    if len(points) < 3:
        return None
    x = points[:, 0].astype(float)
    y = points[:, 1].astype(float)
    a = np.column_stack([x, y, np.ones(len(x))])
    b = x**2 + y**2
    try:
        result, _, _, _ = np.linalg.lstsq(a, b, rcond=None)
    except Exception:
        return None
    cx = result[0] / 2
    cy = result[1] / 2
    radius = float(np.sqrt(result[2] + cx**2 + cy**2))
    if not np.isfinite(radius):
        return None
    return float(cx), float(cy), radius


def _contour_candidates(frame: np.ndarray, frame_index: int) -> list[tuple]:
    roi, offset_x, offset_y = _crop_roi(frame)
    _, bright = cv2.threshold(roi, BRIGHT_PIXEL_THRESHOLD, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    bright = cv2.morphologyEx(bright, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(bright, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    useful = [contour for contour in contours if cv2.contourArea(contour) >= 20]
    candidates = []
    for contour in useful:
        (cx, cy), radius = cv2.minEnclosingCircle(contour)
        if HOUGH_MIN_RADIUS <= radius <= HOUGH_MAX_RADIUS:
            candidates.append((cx + offset_x, cy + offset_y, radius, "contour_enclosing", frame_index))
        fit = _fit_circle_lstsq(contour.reshape(-1, 2))
        if fit is not None:
            fx, fy, fr = fit
            if HOUGH_MIN_RADIUS <= fr <= HOUGH_MAX_RADIUS:
                candidates.append((fx + offset_x, fy + offset_y, fr, "contour_lstsq", frame_index))
    if len(useful) >= 2:
        fit = _fit_circle_lstsq(np.vstack([contour.reshape(-1, 2) for contour in useful]))
        if fit is not None:
            fx, fy, fr = fit
            if HOUGH_MIN_RADIUS <= fr <= HOUGH_MAX_RADIUS:
                candidates.append((fx + offset_x, fy + offset_y, fr, "all_contours_lstsq", frame_index))
    return _unique_candidates(candidates)


def _score_candidate(
    evaluation_frames: list[np.ndarray],
    candidate: tuple,
    exit_index: int,
) -> CircleCandidate:
    cx, cy, radius, method, source_frame = candidate
    frame_evidence = []
    active_values = []
    perimeter_values = []
    for frame in evaluation_frames:
        _, signal = _perimeter_signal(frame, cx, cy, radius)
        active = int(np.count_nonzero(signal > 0))
        perimeter_sum = float(signal.sum())
        active_values.append(active)
        perimeter_values.append(perimeter_sum)
        if active >= 3:
            frame_evidence.append(perimeter_sum + active * 4.0)
    support_frames = len(frame_evidence)
    active = int(round(float(np.median(active_values)))) if active_values else 0
    perimeter_sum = float(np.median(perimeter_values)) if perimeter_values else 0.0
    evidence = float(np.median(frame_evidence)) if frame_evidence else 0.0
    score = (
        evidence
        + support_frames * 25.0
        - abs(source_frame - exit_index) * 0.5
        - abs(radius - 165.0) * 0.08
    )
    if support_frames == 0:
        score -= 1000.0
    return CircleCandidate(
        cx=float(cx),
        cy=float(cy),
        radius=float(radius),
        method=method,
        score=float(score),
        support_frames=support_frames,
        source_frame=source_frame,
        active_samples=active,
        perimeter_sum=perimeter_sum,
    )


def detect_circle(frames: list[np.ndarray], exit_index: int) -> Optional[CircleCandidate]:
    start = max(0, exit_index + SEARCH_START_OFFSET)
    end = min(len(frames), start + SEARCH_FRAME_COUNT)
    frame_best: list[CircleCandidate] = []
    for frame_index in range(start, end):
        raw = _hough_candidates(frames[frame_index], frame_index)
        raw.extend(_contour_candidates(frames[frame_index], frame_index))
        raw = _unique_candidates(raw)
        scored = [_score_candidate([frames[frame_index]], candidate, frame_index) for candidate in raw]
        scored.sort(key=lambda candidate: candidate.score, reverse=True)
        if scored and scored[0].support_frames > 0:
            frame_best.append(scored[0])

    if not frame_best:
        return None
    centers_x = np.array([candidate.cx for candidate in frame_best])
    centers_y = np.array([candidate.cy for candidate in frame_best])
    radii = np.array([candidate.radius for candidate in frame_best])
    median_x = float(np.median(centers_x))
    median_y = float(np.median(centers_y))
    median_r = float(np.median(radii))
    inliers = [
        candidate
        for candidate in frame_best
        if np.hypot(candidate.cx - median_x, candidate.cy - median_y) <= 25.0
        and abs(candidate.radius - median_r) <= 20.0
    ] or frame_best
    return CircleCandidate(
        cx=float(np.mean([candidate.cx for candidate in inliers])),
        cy=float(np.mean([candidate.cy for candidate in inliers])),
        radius=float(np.mean([candidate.radius for candidate in inliers])),
        method="promedio_temporal",
        score=float(np.mean([candidate.score for candidate in inliers])),
        support_frames=len(inliers),
        source_frame=start,
        active_samples=int(round(float(np.mean([candidate.active_samples for candidate in inliers])))),
        perimeter_sum=float(np.mean([candidate.perimeter_sum for candidate in inliers])),
    )


def _arc_clockwise_bounds(theta: np.ndarray, active: np.ndarray) -> tuple[float, float]:
    n = len(theta)
    min_gap_samples = max(1, int(round(n * PERIMETER_MIN_GAP_DEG / 360.0)))
    clock_all = (np.degrees(theta) + 90.0) % 360.0
    order = np.argsort(clock_all)
    active_mask = np.zeros(n, dtype=bool)
    active_mask[active] = True
    active_ordered = active_mask[order]
    clock_ordered = clock_all[order]

    if np.all(active_ordered):
        return float(clock_ordered[0]), float(clock_ordered[-1])
    if not np.any(active_ordered):
        return 0.0, 0.0

    active3 = np.tile(active_ordered, 3).copy()
    padded = np.concatenate([[True], active3, [True]])
    diff = np.diff(padded.astype(np.int8))
    falls = np.where(diff == -1)[0]
    rises = np.where(diff == 1)[0]
    for fall, rise in zip(falls, rises):
        if (rise - fall) < min_gap_samples:
            active3[fall:rise] = True
    active_closed = active3[n : 2 * n]

    inactive2 = np.tile(~active_closed, 2)
    padded2 = np.concatenate([[False], inactive2, [False]])
    diff2 = np.diff(padded2.astype(np.int8))
    gap_starts = np.where(diff2 == 1)[0]
    gap_ends = np.where(diff2 == -1)[0]
    valid = gap_starts < n
    starts = gap_starts[valid]
    ends = gap_ends[valid]
    if len(starts) == 0:
        return float(clock_ordered[0]), float(clock_ordered[-1])

    best = int(np.argmax(ends - starts))
    start_base = int(ends[best]) % n
    end_base = (int(starts[best]) - 1) % n

    arc_start = float(clock_ordered[start_base])
    for offset in range(n):
        idx = (start_base + offset) % n
        if active_ordered[idx]:
            arc_start = float(clock_ordered[idx])
            break

    arc_end = float(clock_ordered[end_base])
    for offset in range(n):
        idx = (end_base - offset) % n
        if active_ordered[idx]:
            arc_end = float(clock_ordered[idx])
            break
    return arc_start, arc_end


def _trailing_component_angle(
    frame: np.ndarray, cx: float, cy: float, radius: float
) -> Optional[float]:
    yy, xx = np.indices(frame.shape)
    radial_distance = np.hypot(xx - cx, yy - cy)
    annulus = (
        (radial_distance >= max(0.0, radius - TRAILING_COMPONENT_INNER_MARGIN))
        & (radial_distance <= radius + TRAILING_COMPONENT_OUTER_MARGIN)
    )
    mask = ((frame >= TRAILING_COMPONENT_THRESHOLD) & annulus).astype(np.uint8) * 255
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    candidates = []
    for label_id in range(1, count):
        area = int(stats[label_id, cv2.CC_STAT_AREA])
        if area < TRAILING_COMPONENT_MIN_AREA:
            continue
        ys, xs = np.where(labels == label_id)
        intensities = frame[ys, xs].astype(float)
        if intensities.sum() <= 0:
            continue
        angles = np.degrees(np.arctan2(xs - cx, -(ys - cy))) % 360.0
        sin_mean = np.average(np.sin(np.radians(angles)), weights=intensities)
        cos_mean = np.average(np.cos(np.radians(angles)), weights=intensities)
        center_angle = math.degrees(math.atan2(sin_mean, cos_mean)) % 360.0
        relative = ((angles - center_angle + 180.0) % 360.0) - 180.0
        trailing_edge = (center_angle + float(np.percentile(relative, 5))) % 360.0
        distance_to_zero = min(center_angle, 360.0 - center_angle)
        candidates.append((distance_to_zero, -area, trailing_edge))
    return float(min(candidates)[2]) if candidates else None


def compute_angle(frame: np.ndarray, circle: CircleCandidate) -> tuple[Optional[float], str, np.ndarray, np.ndarray]:
    theta, signal = _perimeter_signal(frame, circle.cx, circle.cy, circle.radius)
    active = np.flatnonzero(signal > 0)
    if not len(active):
        return None, "SIN_SENAL", theta, signal
    angle = _trailing_component_angle(
        frame, circle.cx, circle.cy, circle.radius
    )
    if angle is None:
        angle, _ = _arc_clockwise_bounds(theta, active)
    confidence = "ALTA" if len(active) >= 10 else "MEDIA"
    return round(angle, 1), confidence, theta, signal


def is_optimal_angle(angle: float) -> bool:
    return 0.0 <= angle <= 90.0


def _has_dark_previous_frame(frames: list[np.ndarray], exit_index: int) -> bool:
    return any(
        float(apply_roi(frame).mean()) < DARK_SCENE_MEAN_THRESHOLD
        for frame in frames[:exit_index]
    )


def _sector_points(
    center: tuple[int, int], radius: int, angle: float
) -> np.ndarray:
    samples = np.linspace(0.0, angle, max(2, int(math.ceil(angle)) + 1))
    points = [center]
    for sample in samples:
        radians = math.radians(90.0 - sample)
        points.append(
            (
                int(round(center[0] + radius * math.cos(radians))),
                int(round(center[1] - radius * math.sin(radians))),
            )
        )
    return np.asarray(points, dtype=np.int32)


def _draw_degree_label(
    image: np.ndarray,
    value: int,
    position: tuple[int, int],
) -> None:
    text = str(value)
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.58
    thickness = 2
    cv2.putText(
        image,
        text,
        position,
        font,
        scale,
        (255, 255, 255),
        thickness,
        cv2.LINE_AA,
    )
    text_width, _ = cv2.getTextSize(text, font, scale, thickness)[0]
    degree_center = (position[0] + text_width + 6, position[1] - 12)
    cv2.circle(image, degree_center, 4, (255, 255, 255), 2, cv2.LINE_AA)


def _angle_endpoint(
    center: tuple[int, int],
    radius: float,
    angle: float,
) -> tuple[int, int]:
    radians = math.radians(90.0 - angle)
    return (
        int(center[0] + radius * math.cos(radians)),
        int(center[1] - radius * math.sin(radians)),
    )


def _draw_dashed_line(
    image: np.ndarray,
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, int, int],
    thickness: int,
    dash_length: int = 18,
    gap_length: int = 10,
) -> None:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length <= 0:
        return
    ux = dx / length
    uy = dy / length
    distance = 0.0
    while distance < length:
        segment_end = min(distance + dash_length, length)
        point_a = (
            int(round(start[0] + ux * distance)),
            int(round(start[1] + uy * distance)),
        )
        point_b = (
            int(round(start[0] + ux * segment_end)),
            int(round(start[1] + uy * segment_end)),
        )
        cv2.line(image, point_a, point_b, color, thickness, cv2.LINE_AA)
        distance += dash_length + gap_length


def _save_diagnostic(
    frame: np.ndarray,
    circle: CircleCandidate,
    angle: Optional[float],
    theta: np.ndarray,
    signal: np.ndarray,
    output_path: Path,
    title: str,
) -> None:
    annotated = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    border_x = 240
    border_y = 130
    annotated = cv2.copyMakeBorder(
        annotated,
        border_y,
        border_y,
        border_x,
        border_x,
        cv2.BORDER_CONSTANT,
        value=(0, 0, 0),
    )
    center = (
        int(circle.cx) + border_x,
        int(circle.cy) + border_y,
    )
    radius = int(circle.radius)
    result_color_bgr = (0, 180, 0)
    result_color_plot = "#16a34a"
    result_text = "OPTIMO - EN RANGO"
    legend_bounds = None
    if angle is not None and not is_optimal_angle(angle):
        result_color_bgr = (0, 0, 220)
        result_color_plot = "#dc2626"
        result_text = "FUERA DE RANGO"

    if angle is not None:
        overlay = annotated.copy()
        cv2.fillPoly(
            overlay,
            [_sector_points(center, radius, angle)],
            result_color_bgr,
        )
        annotated = cv2.addWeighted(overlay, 0.48, annotated, 0.52, 0)

    # Ejes de 0/180 y 90/270 grados para separar los cuatro cuadrantes.
    cv2.line(
        annotated,
        (center[0], center[1] - radius),
        (center[0], center[1] + radius),
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.line(
        annotated,
        (center[0] - radius, center[1]),
        (center[0] + radius, center[1]),
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.circle(annotated, center, radius, (0, 220, 220), 2)
    cv2.circle(annotated, center, 4, (0, 220, 0), -1)

    angle_labels = (
        (0, (center[0] - 12, center[1] - radius - 12)),
        (90, (center[0] + radius + 10, center[1] + 7)),
        (180, (center[0] - 25, center[1] + radius + 24)),
        (270, (center[0] - radius - 48, center[1] + 7)),
    )
    for value, label_point in angle_labels:
        _draw_degree_label(annotated, value, label_point)

    for bound_angle in (225.0, 315.0):
        _draw_dashed_line(
            annotated,
            center,
            _angle_endpoint(center, circle.radius, bound_angle),
            (0, 220, 0),
            3,
        )

    if angle is not None:
        endpoint = _angle_endpoint(center, circle.radius, angle)
        cv2.line(annotated, center, endpoint, result_color_bgr, 4, cv2.LINE_AA)
        cv2.circle(
            annotated,
            endpoint,
            8,
            result_color_bgr,
            -1,
            cv2.LINE_AA,
        )
        cv2.circle(
            annotated,
            endpoint,
            10,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        legend = f"{angle:.1f} grados"
        text_size, baseline = cv2.getTextSize(
            legend,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            2,
        )
        direction_x = endpoint[0] - center[0]
        direction_y = endpoint[1] - center[1]
        if abs(direction_y) > abs(direction_x) * 1.2:
            text_x = endpoint[0] - text_size[0] // 2
            if direction_y < 0:
                box_bottom = center[1] - radius - 65
                text_y = box_bottom - baseline - 7
            else:
                box_top = center[1] + radius + 65
                text_y = box_top + text_size[1] + 7
        else:
            text_y = endpoint[1] + text_size[1] // 2
            if direction_x >= 0:
                text_x = center[0] + radius + 70
            else:
                text_x = center[0] - radius - text_size[0] - 70
        text_x = max(
            10,
            min(text_x, annotated.shape[1] - text_size[0] - 10),
        )
        text_y = max(
            text_size[1] + 10,
            min(text_y, annotated.shape[0] - baseline - 10),
        )
        box_left = text_x - 7
        box_top = text_y - text_size[1] - 7
        box_right = text_x + text_size[0] + 7
        box_bottom = text_y + baseline + 7
        legend_bounds = (box_left, box_top, box_right, box_bottom)
        cv2.rectangle(
            annotated,
            (box_left, box_top),
            (box_right, box_bottom),
            (0, 0, 0),
            -1,
        )
        cv2.putText(
            annotated,
            legend,
            (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            result_color_bgr,
            2,
            cv2.LINE_AA,
        )

    horizontal_margin = max(260, int(round(radius * 1.35)))
    vertical_margin = max(130, int(round(radius * 0.9)))
    crop_x0 = max(0, center[0] - radius - horizontal_margin)
    crop_x1 = min(annotated.shape[1], center[0] + radius + horizontal_margin)
    crop_y0 = max(0, center[1] - radius - vertical_margin)
    crop_y1 = min(annotated.shape[0], center[1] + radius + vertical_margin)
    if legend_bounds is not None:
        box_left, box_top, box_right, box_bottom = legend_bounds
        crop_x0 = max(0, min(crop_x0, box_left - 25))
        crop_x1 = min(annotated.shape[1], max(crop_x1, box_right + 25))
        crop_y0 = max(0, min(crop_y0, box_top - 25))
        crop_y1 = min(annotated.shape[0], max(crop_y1, box_bottom + 25))
    diagnostic_roi = annotated[crop_y0:crop_y1, crop_x0:crop_x1]

    figure = plt.figure(figsize=(12, 9))
    figure.suptitle(title)
    image_axis = figure.add_subplot(1, 1, 1)
    image_axis.imshow(cv2.cvtColor(diagnostic_roi, cv2.COLOR_BGR2RGB))
    image_axis.set_title(
        f"Angulo: {angle if angle is not None else 'N/A'} grados | {result_text}",
        color=result_color_plot if angle is not None else "black",
        fontweight="bold",
        fontsize=18,
        pad=12,
    )
    image_axis.axis("off")
    figure.tight_layout()
    figure.savefig(output_path, dpi=130)
    plt.close(figure)


def _save_failure_diagnostic(
    frame: np.ndarray, output_path: Path, title: str, reason: str
) -> None:
    figure, axis = plt.subplots(figsize=(12, 7))
    axis.imshow(frame, cmap="gray", vmin=0, vmax=255)
    axis.set_title(reason, color="red", fontsize=16, fontweight="bold")
    axis.axis("off")
    figure.suptitle(title)
    figure.tight_layout()
    figure.savefig(output_path, dpi=130)
    plt.close(figure)


def analyze_sequence(folder: str | Path) -> SequenceAnalysisResult:
    folder = Path(folder)
    frames = load_sequence(folder)
    if len(frames) < 2:
        raise RuntimeError("La rafaga no contiene suficientes imagenes BMP")

    exit_index, scene, mean_background, exit_confidence = detect_first_exit(frames)
    circle = detect_circle(frames, exit_index) if exit_index is not None else None
    angle = None
    angle_frame = None
    angle_confidence = "SIN_CIRCULO"
    diagnostic_path = None

    if circle is not None and exit_index is not None:
        candidates = [exit_index, min(exit_index + 1, len(frames) - 1)]
        theta = signal = None
        if not _has_dark_previous_frame(frames, exit_index):
            angle_confidence = "SIN_FONDO_PREVIO"
            angle_frame = exit_index + 1
            theta, signal = _perimeter_signal(frames[exit_index], circle.cx, circle.cy, circle.radius)
        else:
            for index in candidates:
                angle, angle_confidence, theta, signal = compute_angle(frames[index], circle)
                angle_frame = index + 1
                if angle is not None:
                    break
        diagnostic = folder / "resultado_analisis.png"
        _save_diagnostic(
            frames[angle_frame - 1],
            circle,
            angle,
            theta,
            signal,
            diagnostic,
            f"{folder.name} | frame de salida {exit_index + 1}",
        )
        diagnostic_path = str(diagnostic)
    else:
        diagnostic = folder / "resultado_analisis.png"
        if exit_index is None:
            reason = "No se detecto el frame de salida"
            diagnostic_frame = frames[0]
        else:
            reason = "No se detecto el circulo"
            diagnostic_frame = frames[exit_index]
        _save_failure_diagnostic(
            diagnostic_frame,
            diagnostic,
            folder.name,
            reason,
        )
        diagnostic_path = str(diagnostic)

    result = SequenceAnalysisResult(
        total_frames=len(frames),
        scene=scene,
        mean_background=round(mean_background, 2),
        first_exit_frame=exit_index + 1 if exit_index is not None else None,
        exit_confidence=exit_confidence,
        circle_cx=round(circle.cx, 2) if circle else None,
        circle_cy=round(circle.cy, 2) if circle else None,
        circle_radius=round(circle.radius, 2) if circle else None,
        circle_method=circle.method if circle else None,
        circle_support_frames=circle.support_frames if circle else 0,
        angle_frame=angle_frame,
        exit_angle_deg=angle,
        angle_confidence=angle_confidence,
        diagnostic_path=diagnostic_path,
    )
    with (folder / "metricas.json").open("w", encoding="utf-8") as output:
        json.dump(asdict(result), output, ensure_ascii=False, indent=2)
    return result
