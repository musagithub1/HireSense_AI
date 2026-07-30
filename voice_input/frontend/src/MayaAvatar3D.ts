import * as THREE from "three";

import mayaBlinkUrl from "./assets/maya-blink.webp";
import mayaNeutralUrl from "./assets/maya-neutral.webp";
import mayaSpeakAUrl from "./assets/maya-speak-a.webp";
import mayaSpeakOUrl from "./assets/maya-speak-o.webp";

export type MayaState =
  | "ready"
  | "listening"
  | "processing"
  | "speaking"
  | "paused"
  | "error"
  | "offline";

export type MayaViseme = "rest" | "A" | "E" | "I" | "O" | "U";

type MayaAvatarOptions = {
  canvas: HTMLCanvasElement;
  onUnavailable: () => void;
};

type VisemeEvent = {
  viseme?: MayaViseme;
  intensity?: number;
};

type PortraitFrame = "neutral" | "speak-a" | "speak-o" | "blink";

const PORTRAIT_URLS: Record<PortraitFrame, string> = {
  neutral: mayaNeutralUrl,
  "speak-a": mayaSpeakAUrl,
  "speak-o": mayaSpeakOUrl,
  blink: mayaBlinkUrl,
};

function clamp(value: number, minimum = 0, maximum = 1): number {
  return Math.max(minimum, Math.min(maximum, value));
}

function damp(
  current: number,
  target: number,
  smoothing: number,
  delta: number,
): number {
  return THREE.MathUtils.damp(current, target, smoothing, delta);
}

function makePortraitGeometry(): THREE.PlaneGeometry {
  const width = 2.48;
  const height = 2.91;
  const geometry = new THREE.PlaneGeometry(width, height, 12, 14);
  const positions = geometry.attributes.position;

  for (let index = 0; index < positions.count; index += 1) {
    const normalizedX = positions.getX(index) / (width / 2);
    const normalizedY = positions.getY(index) / (height / 2);
    const edgeCurve = -Math.pow(normalizedX, 2) * 0.055;
    const shoulderDepth =
      normalizedY < -0.38
        ? Math.pow((-normalizedY - 0.38) / 0.62, 2) * -0.018
        : 0;
    positions.setZ(index, edgeCurve + shoulderDepth);
  }
  geometry.computeVertexNormals();
  return geometry;
}

function disposeObject(root: THREE.Object3D): void {
  root.traverse((child) => {
    if (!(child instanceof THREE.Mesh)) return;
    child.geometry.dispose();
    const materials = Array.isArray(child.material)
      ? child.material
      : [child.material];
    for (const material of materials) material.dispose();
  });
}

export class MayaAvatar3D {
  private readonly canvas: HTMLCanvasElement;
  private readonly onUnavailable: () => void;
  private readonly renderer: THREE.WebGLRenderer;
  private readonly scene = new THREE.Scene();
  private readonly camera = new THREE.PerspectiveCamera(30, 1, 0.1, 50);
  private readonly avatar = new THREE.Group();
  private readonly portraitMaterial = new THREE.MeshBasicMaterial({
    color: 0xffffff,
    transparent: true,
    opacity: 0,
    toneMapped: false,
  });
  private readonly portrait = new THREE.Mesh(
    makePortraitGeometry(),
    this.portraitMaterial,
  );
  private readonly textures: Partial<Record<PortraitFrame, THREE.Texture>> = {};
  private readonly resizeObserver: ResizeObserver;
  private readonly clock = new THREE.Clock();
  private readonly reducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)",
  ).matches;

  private animationFrame: number | null = null;
  private state: MayaState = "ready";
  private supportMode = false;
  private viseme: MayaViseme = "rest";
  private visemeIntensity = 0;
  private pointerX = 0;
  private pointerY = 0;
  private currentFrame: PortraitFrame | null = null;
  private destroyed = false;

  constructor({ canvas, onUnavailable }: MayaAvatarOptions) {
    this.canvas = canvas;
    this.onUnavailable = onUnavailable;

    this.renderer = new THREE.WebGLRenderer({
      canvas,
      alpha: true,
      antialias: true,
      powerPreference: "high-performance",
      preserveDrawingBuffer: false,
    });
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.setClearColor(0x000000, 0);

    this.camera.position.set(0, 0.015, 5.5);
    this.camera.lookAt(0, 0.015, 0);

    this.portrait.name = "maya-cinematic-portrait";
    this.avatar.add(this.portrait);
    this.scene.add(this.avatar);

    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(canvas);
    canvas.addEventListener("pointermove", this.handlePointerMove);
    canvas.addEventListener("pointerleave", this.handlePointerLeave);
    canvas.addEventListener("webglcontextlost", this.handleContextLost);

    this.resize();
    void this.loadPortraitFrames();
    this.animationFrame = window.requestAnimationFrame(this.animate);
  }

  setState(state: MayaState): void {
    this.state = state;
  }

  setSupportMode(enabled: boolean): void {
    this.supportMode = Boolean(enabled);
  }

  setViseme(detail: VisemeEvent): void {
    const next = detail.viseme ?? "rest";
    this.viseme = ["rest", "A", "E", "I", "O", "U"].includes(next)
      ? next
      : "rest";
    this.visemeIntensity = clamp(Number(detail.intensity ?? 1));
  }

  destroy(): void {
    if (this.destroyed) return;
    this.destroyed = true;
    if (this.animationFrame !== null) {
      window.cancelAnimationFrame(this.animationFrame);
      this.animationFrame = null;
    }
    this.resizeObserver.disconnect();
    this.canvas.removeEventListener("pointermove", this.handlePointerMove);
    this.canvas.removeEventListener("pointerleave", this.handlePointerLeave);
    this.canvas.removeEventListener(
      "webglcontextlost",
      this.handleContextLost,
    );
    for (const texture of Object.values(this.textures)) texture?.dispose();
    disposeObject(this.scene);
    this.renderer.dispose();
    this.renderer.forceContextLoss();
  }

  private async loadPortraitFrames(): Promise<void> {
    const loader = new THREE.TextureLoader();

    try {
      const neutral = await loader.loadAsync(PORTRAIT_URLS.neutral);
      if (this.destroyed) {
        neutral.dispose();
        return;
      }
      this.configureTexture(neutral);
      this.textures.neutral = neutral;
      this.setPortraitFrame("neutral");
      this.portraitMaterial.opacity = 1;
    } catch {
      if (!this.destroyed) this.onUnavailable();
      return;
    }

    await Promise.all(
      (["speak-a", "speak-o", "blink"] as PortraitFrame[]).map(
        async (frame) => {
          try {
            const texture = await loader.loadAsync(PORTRAIT_URLS[frame]);
            if (this.destroyed) {
              texture.dispose();
              return;
            }
            this.configureTexture(texture);
            this.textures[frame] = texture;
          } catch {
            this.textures[frame] = this.textures.neutral;
          }
        },
      ),
    );
  }

  private configureTexture(texture: THREE.Texture): void {
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.minFilter = THREE.LinearMipmapLinearFilter;
    texture.magFilter = THREE.LinearFilter;
    texture.anisotropy = Math.min(
      4,
      this.renderer.capabilities.getMaxAnisotropy(),
    );
    texture.needsUpdate = true;
  }

  private setPortraitFrame(frame: PortraitFrame): void {
    const texture = this.textures[frame] ?? this.textures.neutral;
    if (!texture) return;
    if (frame === this.currentFrame && this.portraitMaterial.map === texture) {
      return;
    }
    this.currentFrame = frame;
    this.portraitMaterial.map = texture;
    this.portraitMaterial.needsUpdate = true;
  }

  private resize(): void {
    const width = Math.max(1, this.canvas.clientWidth);
    const height = Math.max(1, this.canvas.clientHeight);
    const pixelRatio = Math.min(
      window.devicePixelRatio || 1,
      width < 220 ? 1.5 : 2,
    );
    this.renderer.setPixelRatio(pixelRatio);
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
  }

  private handlePointerMove = (event: PointerEvent): void => {
    const bounds = this.canvas.getBoundingClientRect();
    if (!bounds.width || !bounds.height) return;
    this.pointerX = clamp(
      ((event.clientX - bounds.left) / bounds.width) * 2 - 1,
      -1,
      1,
    );
    this.pointerY = clamp(
      -(((event.clientY - bounds.top) / bounds.height) * 2 - 1),
      -1,
      1,
    );
  };

  private handlePointerLeave = (): void => {
    this.pointerX = 0;
    this.pointerY = 0;
  };

  private handleContextLost = (event: Event): void => {
    event.preventDefault();
    this.onUnavailable();
  };

  private shouldBlink(elapsed: number): boolean {
    if (this.reducedMotion || this.state === "paused") return false;
    const phase = (elapsed + 0.65) % 5.2;
    if (phase < 0.13) return true;
    return phase > 0.22 && phase < 0.3 && elapsed % 15 < 5.2;
  }

  private speakingFrame(elapsed: number): PortraitFrame {
    if (this.state !== "speaking") return "neutral";
    if (["O", "U"].includes(this.viseme)) return "speak-o";
    if (["A", "E", "I"].includes(this.viseme)) return "speak-a";
    return Math.sin(elapsed * 8.6) > -0.15 ? "speak-a" : "neutral";
  }

  private updatePortrait(elapsed: number, delta: number): void {
    const motion = this.reducedMotion ? 0 : 1;
    let targetX = this.pointerY * -0.012;
    let targetY = this.pointerX * 0.022;
    let targetZ = 0;

    if (this.state === "speaking") {
      targetX += Math.sin(elapsed * 1.32) * 0.012 * motion;
      targetY += Math.sin(elapsed * 0.77) * 0.017 * motion;
      targetZ = Math.sin(elapsed * 0.94) * 0.005 * motion;
    } else if (this.state === "listening") {
      const nodPhase = elapsed % 5.4;
      const nod =
        nodPhase > 4.12 && nodPhase < 4.72
          ? Math.sin(((nodPhase - 4.12) / 0.6) * Math.PI) * 0.028
          : 0;
      targetX += nod * motion;
      targetY *= 0.42;
    } else if (this.state === "processing") {
      targetX = -0.014 * motion;
      targetY = 0.034 * motion;
    } else if (this.state === "error" || this.state === "offline") {
      targetX = 0.012;
      targetZ = -0.008;
    }

    this.avatar.rotation.x = damp(
      this.avatar.rotation.x,
      targetX,
      4.4,
      delta,
    );
    this.avatar.rotation.y = damp(
      this.avatar.rotation.y,
      targetY,
      4.4,
      delta,
    );
    this.avatar.rotation.z = damp(
      this.avatar.rotation.z,
      targetZ,
      4.4,
      delta,
    );

    const breathe = Math.sin(elapsed * 1.24) * 0.004 * motion;
    const supportLift = this.supportMode ? 0.004 : 0;
    this.avatar.position.y = damp(
      this.avatar.position.y,
      breathe + supportLift,
      3.8,
      delta,
    );
    const targetScale = 1 + breathe * 0.28;
    const nextScale = damp(this.avatar.scale.x, targetScale, 4.2, delta);
    this.avatar.scale.setScalar(nextScale);

    const targetTint = new THREE.Color(
      this.supportMode ? 0xfff9f4 : 0xffffff,
    );
    this.portraitMaterial.color.lerp(targetTint, clamp(delta * 4.5));

    const frame = this.shouldBlink(elapsed)
      ? "blink"
      : this.speakingFrame(elapsed);
    this.setPortraitFrame(frame);
    this.visemeIntensity = Math.max(
      this.state === "speaking" ? 0.24 : 0,
      this.visemeIntensity - delta * 1.7,
    );
  }

  private animate = (): void => {
    if (this.destroyed) return;
    const delta = Math.min(0.05, this.clock.getDelta());
    const elapsed = this.clock.elapsedTime;
    this.updatePortrait(elapsed, delta);
    this.renderer.render(this.scene, this.camera);
    this.animationFrame = window.requestAnimationFrame(this.animate);
  };
}
