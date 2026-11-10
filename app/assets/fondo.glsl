precision highp float;

uniform vec2 uRes;
uniform float uT;
uniform float uP;
uniform float uCalm;
uniform float uMotion;

// ruido fino pixel a pixel
float hash12(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}

float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
  return mix(mix(hash12(i), hash12(i + vec2(1.0, 0.0)), u.x),
             mix(hash12(i + vec2(0.0, 1.0)), hash12(i + vec2(1.0, 1.0)), u.x), u.y);
}

float fbm(vec2 p) {
  float v = 0.0;
  float a = 0.5;
  mat2 rot = mat2(0.8, 0.6, -0.6, 0.8);
  for (int i = 0; i < 5; i++) {
    v += a * noise(p);
    p = rot * p * 2.02 + vec2(13.1, 7.7);
    a *= 0.5;
  }
  return v;
}

void main() {
  vec2 uv = gl_FragCoord.xy / uRes;
  uv.y = 1.0 - uv.y;
  float t = uT * 0.055 * uMotion;

  float p = clamp(uP, 0.0, 2.0);
  float p1 = clamp(p, 0.0, 1.0);
  float p2 = clamp(p - 1.0, 0.0, 1.0);

  // desplazamiento lateral continuo que acompana al scroll
  float panX = p * 0.38;

  // turbulencia base para que el barrido horizontal sea organico y gradual
  float baseWarp = fbm(vec2((uv.x + panX * 0.5) * 1.8, uv.y * 1.2 + t * 0.5));
  float baseWarp2 = fbm(vec2((uv.x - panX * 0.35) * 1.5 - t * 0.3, uv.y * 1.4 + 4.3));

  // avance gradual en horizontal de izquierda a derecha segun bajas con el scroll
  float m1 = smoothstep(0.0, 1.0, p1 * 2.15 - uv.x * 0.9 - (1.0 - p1) * 0.25 + (baseWarp - 0.5) * 0.28 * sin(p1 * 3.14159));
  float m2 = smoothstep(0.0, 1.0, p2 * 2.15 - uv.x * 0.9 - (1.0 - p2) * 0.25 + (baseWarp2 - 0.5) * 0.28 * sin(p2 * 3.14159));

  // inclinacion progresiva de vertical (16/24) a diagonal (21/24)
  float shear = mix(0.0, -0.58, m2);
  float freq = mix(9.2, 7.0, m2);

  // cortes horizontales suaves en la tercera fase
  float row = floor(uv.y * 44.0);
  float slip = step(0.93, hash12(vec2(row, floor(t * 0.7)))) * (hash12(vec2(row, 9.1)) - 0.5) * 0.2 * m2;
  vec2 pUv = vec2(uv.x + slip - panX, uv.y);

  float warp = fbm(vec2(pUv.x * 2.1 + pUv.y * shear, pUv.y * 1.1 + t * 0.65));
  float warp2 = fbm(vec2(pUv.x * 1.4 - t * 0.35, pUv.y * 1.5 + 4.3));

  float coord = (pUv.x * 1.08 + pUv.y * shear) * freq + (warp - 0.5) * 2.4 + t * 0.85;
  float wave = 0.5 + 0.5 * sin(coord * 1.3 + (warp2 - 0.5) * 3.1);
  float secWave = 0.5 + 0.5 * cos(coord * 0.85 - pUv.y * mix(1.8, 0.7, m2) + warp * 2.5);

  // paletas mezcladas de forma gradual a lo largo del eje horizontal
  vec3 redMoah = vec3(0.95, 0.13, 0.075) * (0.94 + 0.1 * warp);

  vec3 darkCol = mix(vec3(0.0, 0.03, 0.085), vec3(0.015, 0.004, 0.07), m2);
  vec3 midDark = mix(vec3(0.42, 0.07, 0.16), vec3(0.055, 0.012, 0.18), m2);
  vec3 warmCol = mix(vec3(1.0, 0.21, 0.16), vec3(0.97, 0.27, 0.07), m2);
  vec3 warmHot = mix(vec3(0.92, 0.38, 0.56), vec3(1.0, 0.45, 0.18), m2);
  vec3 coolCol = mix(vec3(0.36, 0.71, 0.98), vec3(0.54, 0.74, 0.82), m2);

  vec3 surge = mix(darkCol, midDark, smoothstep(0.15, 0.7, warp2));
  float warmMask = smoothstep(0.28, 0.78, wave * 0.82 + warp * 0.28);
  vec3 warmBand = mix(warmCol, warmHot, smoothstep(0.45, 0.9, secWave));
  surge = mix(surge, warmBand, warmMask);

  float coolVert = smoothstep(0.52, 0.88, secWave * (1.0 - warmMask * 0.45)) * (1.0 - m2);
  vec2 ell = (vec2(uv.x - (p1 - 0.5) * 0.18, uv.y) - vec2(0.66, 0.68)) / vec2(0.42, 0.5);
  float dEll = length(ell + (warp - 0.5) * 0.22);
  float core16 = smoothstep(0.95, 0.4, dEll) * (1.0 - m2);
  float halo16 = smoothstep(1.5, 0.9, dEll) * smoothstep(0.35, 0.9, dEll) * (1.0 - m2);

  surge = mix(surge, coolCol, coolVert * 0.88);
  surge = mix(surge, vec3(0.02, 0.1, 0.22), halo16 * 0.7);
  surge = mix(surge, darkCol, core16 * 0.92);

  float bottomMist = smoothstep(0.76, 1.0, uv.y + (warp2 - 0.5) * 0.24) * smoothstep(0.85, 0.15, uv.x);
  float topMist = smoothstep(0.11, 0.0, uv.y + (warp - 0.5) * 0.07);
  float horizGlow = smoothstep(0.028, 0.0, abs(uv.y - 0.18 - (warp2 - 0.5) * 0.04)) * smoothstep(0.75, 0.1, uv.x);
  float coolHoriz = clamp(bottomMist * 0.9 + topMist * 0.75 + horizGlow * 0.8, 0.0, 0.92) * m2;
  surge = mix(surge, coolCol, coolHoriz);

  vec3 col = mix(redMoah, surge, m1);

  // granulado fino 1:1 con el pixel de pantalla
  float g1 = hash12(gl_FragCoord.xy + floor(uT * 9.0 * uMotion));
  float g2 = hash12(gl_FragCoord.xy * 0.5 + 17.3 + floor(uT * 9.0 * uMotion));
  float fineGrain = (g1 * 0.7 + g2 * 0.3) - 0.5;
  float grainAmp = mix(0.045, 0.13, m1);
  col += fineGrain * grainAmp;

  col *= mix(1.0, 0.68, uCalm);
  gl_FragColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}
