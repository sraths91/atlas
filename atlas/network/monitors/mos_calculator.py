"""
MOS (Mean Opinion Score) Calculator - ITU-T E-Model Implementation

Calculates voice/video quality scores based on network metrics using
the ITU-T G.107 E-Model and simplified R-factor calculations.

MOS Scale:
- 5.0: Excellent - Users very satisfied
- 4.0: Good - Users satisfied
- 3.0: Fair - Some users dissatisfied
- 2.0: Poor - Many users dissatisfied
- 1.0: Bad - Nearly all users dissatisfied

This module provides both:
1. Full E-Model calculation (for detailed VoIP quality assessment)
2. Simplified MOS estimation (for quick quality checks)
"""

import math
import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CodecType(Enum):
    """Voice codec types with their impairment factors (Ie)"""
    G711 = ('G.711', 0)       # PCM, 64 kbps - no impairment
    G729 = ('G.729', 11)      # CS-ACELP, 8 kbps
    G723_1_63 = ('G.723.1', 15)  # 6.3 kbps
    G723_1_53 = ('G.723.1', 19)  # 5.3 kbps
    OPUS = ('Opus', 5)        # Modern adaptive codec
    SILK = ('SILK', 8)        # Skype codec
    SPEEX = ('Speex', 10)     # Open source
    AMR_NB = ('AMR-NB', 12)   # GSM mobile
    ILBC = ('iLBC', 10)       # Internet Low Bitrate Codec

    def __init__(self, display_name: str, ie_value: int):
        self.display_name = display_name
        self.ie_value = ie_value


@dataclass
class NetworkMetrics:
    """Network metrics for MOS calculation"""
    latency_ms: float = 0.0      # One-way delay in ms
    jitter_ms: float = 0.0       # Jitter in ms
    packet_loss_percent: float = 0.0  # Packet loss percentage


@dataclass
class MOSResult:
    """Result of MOS calculation"""
    mos: float                    # MOS score 1.0-5.0
    r_factor: float              # R-factor 0-100
    quality_rating: str          # Descriptive rating
    impairments: Dict[str, float]  # Breakdown of impairments
    recommendations: list        # Suggestions for improvement


class MOSCalculator:
    """
    ITU-T G.107 E-Model MOS Calculator.

    The E-Model calculates an R-factor (0-100) based on:
    - Delay impairment (Id)
    - Equipment impairment (Ie-eff) - codec and packet loss effects
    - Simultaneous impairment (Is) - quantization and loudness
    - Advantage factor (A) - user expectation adjustment

    R = R0 - Is - Id - Ie-eff + A

    Then converts R to MOS using the standard formula.
    """

    # E-Model default constants
    R0 = 93.2  # Basic signal-to-noise ratio

    # Delay impairment thresholds (ITU-T G.114)
    DELAY_THRESHOLD_MS = 177.3  # Mouth-to-ear delay threshold

    # Packet loss burst ratio (Bpl) - typical value for random loss
    DEFAULT_BPL = 1.0

    def __init__(
        self,
        codec: CodecType = CodecType.G711,
        advantage_factor: float = 0.0
    ):
        """
        Initialize MOS Calculator.

        Args:
            codec: Voice codec being used
            advantage_factor: A-factor for user expectations
                - 0: Landline quality expected
                - 5: Mobile quality expected
                - 10: Satellite/emergency expected
        """
        self.codec = codec
        self.advantage_factor = advantage_factor

        # Equipment impairment for codec
        self.ie = codec.ie_value

    def calculate_mos(self, metrics: NetworkMetrics) -> MOSResult:
        """
        Calculate MOS score from network metrics.

        Args:
            metrics: NetworkMetrics with latency, jitter, packet_loss

        Returns:
            MOSResult with MOS score and detailed breakdown
        """
        # Calculate individual impairments
        id_factor = self._calculate_delay_impairment(metrics.latency_ms, metrics.jitter_ms)
        ie_eff = self._calculate_equipment_impairment(metrics.packet_loss_percent)
        is_factor = self._calculate_simultaneous_impairment()

        # Calculate R-factor
        r_factor = self.R0 - is_factor - id_factor - ie_eff + self.advantage_factor

        # Clamp R-factor to valid range
        r_factor = max(0, min(100, r_factor))

        # Convert R to MOS
        mos = self._r_to_mos(r_factor)

        # Get quality rating
        quality_rating = self._get_quality_rating(mos)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            metrics, id_factor, ie_eff
        )

        return MOSResult(
            mos=round(mos, 2),
            r_factor=round(r_factor, 1),
            quality_rating=quality_rating,
            impairments={
                'delay_impairment': round(id_factor, 2),
                'equipment_impairment': round(ie_eff, 2),
                'simultaneous_impairment': round(is_factor, 2),
                'advantage_factor': self.advantage_factor,
                'base_r0': self.R0
            },
            recommendations=recommendations
        )

    def _calculate_delay_impairment(
        self,
        latency_ms: float,
        jitter_ms: float
    ) -> float:
        """
        Calculate delay impairment factor (Id).

        Based on ITU-T G.107 formula accounting for:
        - One-way delay (Ta)
        - Jitter buffer delay

        Args:
            latency_ms: One-way network delay
            jitter_ms: Network jitter

        Returns:
            Delay impairment factor Id
        """
        # Total absolute delay (Ta) includes:
        # - Network delay (one-way)
        # - Jitter buffer delay (typically 2x jitter)
        # - Codec delay (assume 20ms for typical VoIP)
        codec_delay = 20.0
        jitter_buffer = jitter_ms * 2.0  # Adaptive jitter buffer

        ta = latency_ms + jitter_buffer + codec_delay

        # ITU-T G.107 delay impairment formula
        if ta <= self.DELAY_THRESHOLD_MS:
            # Below threshold - minimal impairment
            id_factor = 0.024 * ta
        else:
            # Above threshold - exponential impairment increase
            x = (ta - self.DELAY_THRESHOLD_MS) / self.DELAY_THRESHOLD_MS
            id_factor = 0.024 * ta + 0.11 * (ta - self.DELAY_THRESHOLD_MS) * math.exp(-x)

        return id_factor

    def _calculate_equipment_impairment(self, packet_loss: float) -> float:
        """
        Calculate effective equipment impairment factor (Ie-eff).

        Combines codec impairment (Ie) with packet loss effects.

        Args:
            packet_loss: Packet loss percentage

        Returns:
            Effective equipment impairment factor Ie-eff
        """
        # Packet loss robustness factor (Bpl)
        # Higher = more robust to packet loss
        # G.711: Bpl ≈ 25, G.729: Bpl ≈ 10
        bpl = self._get_bpl_for_codec()

        # ITU-T G.107 Ie-eff formula
        if packet_loss <= 0:
            return self.ie

        ie_eff = self.ie + (95 - self.ie) * (packet_loss / (packet_loss + bpl))

        return ie_eff

    def _calculate_simultaneous_impairment(self) -> float:
        """
        Calculate simultaneous impairment factor (Is).

        Includes quantization distortion, sidetone, loudness issues.
        For typical VoIP systems, this is relatively constant.

        Returns:
            Simultaneous impairment factor Is
        """
        # Typical value for modern VoIP systems
        # Composed of: Ist (sidetone) + Iolr (loudness) + Iq (quantization)
        return 1.41

    def _get_bpl_for_codec(self) -> float:
        """Get packet loss robustness factor for current codec"""
        bpl_values = {
            CodecType.G711: 25.1,
            CodecType.G729: 10.0,
            CodecType.G723_1_63: 15.0,
            CodecType.G723_1_53: 19.0,
            CodecType.OPUS: 20.0,  # Opus has good FEC
            CodecType.SILK: 18.0,
            CodecType.SPEEX: 12.0,
            CodecType.AMR_NB: 14.0,
            CodecType.ILBC: 10.0,
        }
        return bpl_values.get(self.codec, 15.0)

    def _r_to_mos(self, r: float) -> float:
        """
        Convert R-factor to MOS using ITU-T G.107 formula.

        Args:
            r: R-factor (0-100)

        Returns:
            MOS score (1.0-5.0)
        """
        if r <= 0:
            return 1.0
        if r >= 100:
            return 4.5  # Maximum achievable MOS

        # ITU-T G.107 formula
        mos = 1 + 0.035 * r + r * (r - 60) * (100 - r) * 7e-6

        # Clamp to valid MOS range
        return max(1.0, min(5.0, mos))

    def _get_quality_rating(self, mos: float) -> str:
        """Convert MOS to quality rating"""
        if mos >= 4.3:
            return 'excellent'
        elif mos >= 4.0:
            return 'good'
        elif mos >= 3.6:
            return 'fair'
        elif mos >= 3.1:
            return 'poor'
        elif mos >= 2.6:
            return 'bad'
        else:
            return 'unusable'

    def _generate_recommendations(
        self,
        metrics: NetworkMetrics,
        id_factor: float,
        ie_eff: float
    ) -> list:
        """Generate recommendations for improving quality"""
        recommendations = []

        # High latency
        if metrics.latency_ms > 150:
            recommendations.append(
                f"High latency ({metrics.latency_ms:.0f}ms) - consider closer servers or better routing"
            )
        elif metrics.latency_ms > 100:
            recommendations.append(
                f"Moderate latency ({metrics.latency_ms:.0f}ms) - acceptable but could be improved"
            )

        # High jitter
        if metrics.jitter_ms > 30:
            recommendations.append(
                f"High jitter ({metrics.jitter_ms:.0f}ms) - network congestion or QoS issues likely"
            )
        elif metrics.jitter_ms > 15:
            recommendations.append(
                f"Moderate jitter ({metrics.jitter_ms:.0f}ms) - consider traffic prioritization"
            )

        # High packet loss
        if metrics.packet_loss_percent > 3:
            recommendations.append(
                f"High packet loss ({metrics.packet_loss_percent:.1f}%) - check network for errors or congestion"
            )
        elif metrics.packet_loss_percent > 1:
            recommendations.append(
                f"Some packet loss ({metrics.packet_loss_percent:.1f}%) - may affect call quality"
            )

        # Codec suggestion
        if ie_eff > 30 and self.codec != CodecType.OPUS:
            recommendations.append(
                "Consider using Opus codec for better packet loss resilience"
            )

        if not recommendations:
            recommendations.append("Network quality is good for voice/video calls")

        return recommendations


# ==================== Simplified MOS Estimation ====================

def estimate_mos_simple(
    latency_ms: float,
    jitter_ms: float,
    packet_loss_percent: float
) -> Tuple[float, str]:
    """
    Quick MOS estimation without full E-Model calculation.

    Useful for dashboard displays and quick assessments.

    Args:
        latency_ms: One-way network latency
        jitter_ms: Network jitter
        packet_loss_percent: Packet loss percentage

    Returns:
        Tuple of (MOS score, quality rating)
    """
    # Start with perfect score
    r = 93.2

    # Deduct for latency (simplified)
    if latency_ms > 0:
        if latency_ms <= 160:
            r -= latency_ms * 0.024
        else:
            r -= 160 * 0.024 + (latency_ms - 160) * 0.1

    # Deduct for jitter (simplified)
    if jitter_ms > 0:
        # Jitter buffer adds delay and can cause packet drops
        r -= jitter_ms * 0.25

    # Deduct for packet loss (most impactful)
    if packet_loss_percent > 0:
        r -= packet_loss_percent * 4.5

    # Clamp R-factor
    r = max(0, min(100, r))

    # Convert to MOS
    if r <= 0:
        mos = 1.0
    elif r >= 100:
        mos = 4.5
    else:
        mos = 1 + 0.035 * r + r * (r - 60) * (100 - r) * 7e-6

    mos = max(1.0, min(5.0, mos))

    # Get rating
    if mos >= 4.3:
        rating = 'excellent'
    elif mos >= 4.0:
        rating = 'good'
    elif mos >= 3.6:
        rating = 'fair'
    elif mos >= 3.1:
        rating = 'poor'
    else:
        rating = 'bad'

    return round(mos, 2), rating


def get_mos_color(mos: float) -> str:
    """Get color for MOS display (for dashboards)"""
    if mos >= 4.0:
        return '#22c55e'  # Green
    elif mos >= 3.6:
        return '#84cc16'  # Lime
    elif mos >= 3.1:
        return '#eab308'  # Yellow
    elif mos >= 2.6:
        return '#f97316'  # Orange
    else:
        return '#ef4444'  # Red


def get_mos_emoji(mos: float) -> str:
    """Get emoji for MOS display"""
    if mos >= 4.3:
        return '🎯'  # Excellent
    elif mos >= 4.0:
        return '✅'  # Good
    elif mos >= 3.6:
        return '⚠️'  # Fair
    elif mos >= 3.1:
        return '🔶'  # Poor
    else:
        return '❌'  # Bad


# ==================== Integration Helper ====================

def calculate_network_mos(
    ping_latency_ms: float,
    jitter_ms: float = 0.0,
    packet_loss_percent: float = 0.0,
    codec: CodecType = CodecType.G711
) -> Dict[str, Any]:
    """
    Calculate MOS from network monitoring metrics.

    This is the main entry point for integration with other monitors.

    Args:
        ping_latency_ms: Ping/RTT latency (will be halved for one-way)
        jitter_ms: Measured jitter
        packet_loss_percent: Packet loss percentage
        codec: Assumed codec (default G.711)

    Returns:
        Dictionary with MOS score and related metrics
    """
    # Convert RTT to one-way delay
    one_way_delay = ping_latency_ms / 2.0

    # Use full E-Model calculator
    calculator = MOSCalculator(codec=codec)
    metrics = NetworkMetrics(
        latency_ms=one_way_delay,
        jitter_ms=jitter_ms,
        packet_loss_percent=packet_loss_percent
    )

    result = calculator.calculate_mos(metrics)

    return {
        'mos': result.mos,
        'r_factor': result.r_factor,
        'quality_rating': result.quality_rating,
        'quality_color': get_mos_color(result.mos),
        'impairments': result.impairments,
        'recommendations': result.recommendations,
        'input_metrics': {
            'latency_ms': ping_latency_ms,
            'one_way_delay_ms': one_way_delay,
            'jitter_ms': jitter_ms,
            'packet_loss_percent': packet_loss_percent,
            'codec': codec.display_name
        }
    }
