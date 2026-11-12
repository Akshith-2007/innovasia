package `in`.kisancoldlink.app.core.design

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun KclCard(modifier: Modifier = Modifier, tint: Color = KclColors.White, content: @Composable ColumnScope.() -> Unit) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        color = tint,
        border = BorderStroke(1.dp, KclColors.Line),
    ) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp), content = content)
    }
}

@Composable
fun SectionTitle(text: String, modifier: Modifier = Modifier) {
    Text(text, style = MaterialTheme.typography.headlineSmall, color = KclColors.ForestDeep, modifier = modifier)
}

@Composable
fun KeyValue(label: String, value: String, valueColor: Color = KclColors.Ink, bold: Boolean = false) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
        Text(label, style = MaterialTheme.typography.bodyMedium, color = KclColors.Muted, modifier = Modifier.weight(1f))
        Spacer(Modifier.width(12.dp))
        Text(
            value, style = MaterialTheme.typography.bodyLarge, color = valueColor,
            fontWeight = if (bold) FontWeight.Bold else FontWeight.Medium, textAlign = TextAlign.End,
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
fun Pill(text: String, background: Color = KclColors.Sage, foreground: Color = KclColors.ForestDeep) {
    Text(
        text, style = MaterialTheme.typography.labelMedium, color = foreground,
        modifier = Modifier.clip(RoundedCornerShape(50)).background(background).padding(horizontal = 12.dp, vertical = 5.dp),
    )
}

@Composable
fun BigButton(
    text: String, onClick: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true,
    icon: ImageVector? = null, container: Color = KclColors.Forest, content: Color = KclColors.White,
) {
    Button(
        onClick = onClick, enabled = enabled, modifier = modifier.fillMaxWidth().heightIn(min = 64.dp),
        shape = RoundedCornerShape(18.dp),
        colors = ButtonDefaults.buttonColors(containerColor = container, contentColor = content),
    ) {
        if (icon != null) {
            Icon(icon, contentDescription = null, modifier = Modifier.size(28.dp))
            Spacer(Modifier.width(10.dp))
        }
        Text(text, style = MaterialTheme.typography.labelLarge, textAlign = TextAlign.Center)
    }
}

@Composable
fun SecondaryButton(text: String, onClick: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true, icon: ImageVector? = null) {
    OutlinedButton(
        onClick = onClick, enabled = enabled, modifier = modifier.fillMaxWidth().heightIn(min = 56.dp),
        shape = RoundedCornerShape(18.dp), border = BorderStroke(2.dp, KclColors.Forest),
    ) {
        if (icon != null) {
            Icon(icon, contentDescription = null, tint = KclColors.Forest)
            Spacer(Modifier.width(8.dp))
        }
        Text(text, style = MaterialTheme.typography.labelLarge, color = KclColors.Forest, textAlign = TextAlign.Center)
    }
}

/** Keypad-style call option: a big number with its meaning underneath. App buttons, not DTMF. */
@Composable
fun NumberOptionButton(number: String, label: String, onClick: () -> Unit, enabled: Boolean, primary: Boolean, modifier: Modifier = Modifier) {
    val bg = if (primary) KclColors.Forest else KclColors.White
    val fg = if (primary) KclColors.White else KclColors.Forest
    Button(
        onClick = onClick, enabled = enabled, modifier = modifier.heightIn(min = 132.dp),
        shape = RoundedCornerShape(24.dp),
        border = if (primary) null else BorderStroke(2.dp, KclColors.Forest),
        colors = ButtonDefaults.buttonColors(
            containerColor = bg, contentColor = fg,
            disabledContainerColor = KclColors.Sage, disabledContentColor = KclColors.Muted,
        ),
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(number, fontSize = 44.sp, fontWeight = FontWeight.Bold)
            Text(label, style = MaterialTheme.typography.titleMedium, textAlign = TextAlign.Center)
        }
    }
}

@Composable
fun LoadingBox(label: String, modifier: Modifier = Modifier) {
    Column(modifier.fillMaxWidth().padding(32.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        CircularProgressIndicator(color = KclColors.Forest)
        Spacer(Modifier.height(14.dp))
        Text(label, style = MaterialTheme.typography.bodyLarge, color = KclColors.Muted)
    }
}

@Composable
fun MessageBox(message: String, modifier: Modifier = Modifier, isError: Boolean = true, action: String? = null, onAction: (() -> Unit)? = null) {
    KclCard(modifier, tint = if (isError) KclColors.DangerSoft else KclColors.Sage) {
        Text(message, style = MaterialTheme.typography.bodyLarge, color = if (isError) KclColors.Danger else KclColors.ForestDeep)
        if (action != null && onAction != null) SecondaryButton(action, onAction)
    }
}

/**
 * Raithanna: an original illustrated village companion (white turban with amber band, moustache,
 * green kurta). Soft rings pulse only while [speaking] is true, i.e. while audio is actually playing.
 */
@Composable
fun RaithannaAvatar(size: Dp, speaking: Boolean = false, modifier: Modifier = Modifier, description: String = "") {
    val pulse = rememberInfiniteTransition(label = "pulse")
    val ring by pulse.animateFloat(0f, 1f, infiniteRepeatable(tween(1400), RepeatMode.Restart), label = "ring")
    Box(modifier.size(size).semantics { contentDescription = description }, contentAlignment = Alignment.Center) {
        Canvas(Modifier.size(size)) {
            val w = this.size.width
            val c = Offset(w / 2, w / 2)
            if (speaking) {
                drawCircle(KclColors.Amber.copy(alpha = 0.35f * (1 - ring)), radius = w * (0.40f + 0.10f * ring), center = c)
            }
            drawCircle(KclColors.Sage, radius = w * 0.40f, center = c)
            // kurta
            drawRoundRect(KclColors.Earth, topLeft = Offset(w * 0.24f, w * 0.66f), size = Size(w * 0.52f, w * 0.30f), cornerRadius = CornerRadius(w * 0.2f))
            // face
            drawOval(KclColors.Skin, topLeft = Offset(w * 0.33f, w * 0.30f), size = Size(w * 0.34f, w * 0.40f))
            // turban
            val turban = Path().apply {
                moveTo(w * 0.30f, w * 0.40f)
                cubicTo(w * 0.28f, w * 0.18f, w * 0.72f, w * 0.18f, w * 0.70f, w * 0.40f)
                lineTo(w * 0.70f, w * 0.43f)
                cubicTo(w * 0.60f, w * 0.37f, w * 0.40f, w * 0.37f, w * 0.30f, w * 0.43f)
                close()
            }
            drawPath(turban, KclColors.White)
            drawPath(turban, KclColors.Line, style = Stroke(width = w * 0.008f))
            drawLine(KclColors.Amber, Offset(w * 0.32f, w * 0.405f), Offset(w * 0.68f, w * 0.405f), strokeWidth = w * 0.025f)
            // eyes, smile, moustache
            drawCircle(KclColors.Hair, radius = w * 0.018f, center = Offset(w * 0.44f, w * 0.49f))
            drawCircle(KclColors.Hair, radius = w * 0.018f, center = Offset(w * 0.56f, w * 0.49f))
            val moustache = Path().apply {
                moveTo(w * 0.41f, w * 0.585f)
                quadraticBezierTo(w * 0.47f, w * 0.545f, w * 0.50f, w * 0.575f)
                quadraticBezierTo(w * 0.53f, w * 0.545f, w * 0.59f, w * 0.585f)
                quadraticBezierTo(w * 0.53f, w * 0.60f, w * 0.50f, w * 0.59f)
                quadraticBezierTo(w * 0.47f, w * 0.60f, w * 0.41f, w * 0.585f)
                close()
            }
            drawPath(moustache, KclColors.Hair)
            drawArc(KclColors.Hair, 20f, 140f, false, topLeft = Offset(w * 0.45f, w * 0.57f), size = Size(w * 0.10f, w * 0.06f), style = Stroke(w * 0.012f))
        }
    }
}

/** Waveform that moves only while audio plays; flat and grey otherwise (no fake listening animation). */
@Composable
fun Waveform(active: Boolean, modifier: Modifier = Modifier) {
    val t = rememberInfiniteTransition(label = "wave")
    val phase by t.animateFloat(0f, 6.283f, infiniteRepeatable(tween(900), RepeatMode.Restart), label = "phase")
    Canvas(modifier.fillMaxWidth().height(48.dp)) {
        val bars = 24
        val gap = size.width / bars
        for (i in 0 until bars) {
            val h = if (active) (0.25f + 0.75f * ((kotlin.math.sin(phase + i * 0.6f) + 1f) / 2f)) else 0.12f
            val bh = size.height * h
            drawRoundRect(
                color = if (active) KclColors.Amber else KclColors.Line,
                topLeft = Offset(i * gap + gap * 0.25f, (size.height - bh) / 2),
                size = Size(gap * 0.5f, bh), cornerRadius = CornerRadius(gap * 0.25f),
            )
        }
    }
}

@Composable
fun CircleIcon(icon: ImageVector, tint: Color, background: Color, modifier: Modifier = Modifier) {
    Box(modifier.size(44.dp).clip(CircleShape).background(background).border(1.dp, KclColors.Line, CircleShape), contentAlignment = Alignment.Center) {
        Icon(icon, contentDescription = null, tint = tint)
    }
}
