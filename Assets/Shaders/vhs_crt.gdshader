// VHS / CRT screen-space post-process — Godot 4.x
//
// Setup: add a CanvasLayer (layer 100) → ColorRect (Anchors: Full Rect,
// Mouse Filter: Ignore) → Material: new ShaderMaterial → Shader: this file.
// Every effect below has its own uniform so you can tune or zero it per scene.
shader_type canvas_item;

uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;

group_uniforms Tracking;
uniform float tracking_jitter : hint_range(0.0, 0.02) = 0.0025;  // per-line horizontal tear
uniform float tracking_band_speed : hint_range(0.0, 1.0) = 0.12; // rolling tracking-error band
uniform float tracking_band_strength : hint_range(0.0, 1.0) = 0.5;

group_uniforms Waves;
uniform float wave_amplitude : hint_range(0.0, 0.01) = 0.0012;   // horizontal micro waves
uniform float wave_frequency : hint_range(0.0, 400.0) = 90.0;
uniform float wave_speed : hint_range(0.0, 20.0) = 3.0;

group_uniforms Colour;
uniform float aberration : hint_range(0.0, 0.02) = 0.0025;       // red/blue edge bleed
uniform float bleed : hint_range(0.0, 0.01) = 0.0015;            // horizontal smear

group_uniforms Scanlines;
uniform float scanline_count : hint_range(60.0, 1080.0) = 270.0;
uniform float scanline_strength : hint_range(0.0, 1.0) = 0.22;

group_uniforms Lens;
uniform float curvature : hint_range(0.0, 0.5) = 0.10;           // bubble lens bulge
uniform float vignette_strength : hint_range(0.0, 2.0) = 0.55;

group_uniforms Grain;
uniform float grain_strength : hint_range(0.0, 0.5) = 0.07;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

vec2 bulge(vec2 uv) {
	uv = uv * 2.0 - 1.0;
	vec2 off = abs(uv.yx) * curvature;
	uv += uv * off * off;
	return uv * 0.5 + 0.5;
}

vec3 sample_rgb(vec2 uv) {
	float r = texture(screen_tex, uv + vec2(aberration, 0.0)).r;
	float g = texture(screen_tex, uv).g;
	float b = texture(screen_tex, uv - vec2(aberration, 0.0)).b;
	return vec3(r, g, b);
}

void fragment() {
	vec2 uv = bulge(SCREEN_UV);
	if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
		COLOR = vec4(0.0, 0.0, 0.0, 1.0);
	} else {
		float t = TIME;

		// rolling tracking-error band (travels bottom → top)
		float band_y = 1.0 - fract(t * tracking_band_speed);
		float band = smoothstep(0.04, 0.0, abs(uv.y - band_y)) * tracking_band_strength;

		// per-line jitter, re-rolled ~24 times a second like tape frames
		float line = floor(uv.y * scanline_count);
		float frame = floor(t * 24.0);
		float jitter = (hash(vec2(line, frame)) - 0.5) * tracking_jitter;
		jitter += band * (hash(vec2(frame, line * 0.37)) - 0.5) * 0.05;

		float wave = sin(uv.y * wave_frequency + t * wave_speed) * wave_amplitude;
		vec2 duv = uv + vec2(jitter + wave, 0.0);

		vec3 col = sample_rgb(duv) * 0.6
			+ sample_rgb(duv + vec2(bleed, 0.0)) * 0.25
			+ sample_rgb(duv + vec2(bleed * 2.0, 0.0)) * 0.15;

		// scanlines
		float scan = 0.5 + 0.5 * cos(uv.y * scanline_count * TAU);
		col *= 1.0 - scanline_strength * (1.0 - scan);

		// band noise + grain
		col += band * 0.25 * (hash(uv * 800.0 + t) - 0.3);
		col += (hash(uv * vec2(1920.0, 1080.0) + fract(t * 7.0)) - 0.5) * grain_strength;

		// vignette
		vec2 v = uv - 0.5;
		col *= clamp(1.0 - dot(v, v) * vignette_strength * 2.2, 0.0, 1.0);

		COLOR = vec4(col, 1.0);
	}
}
