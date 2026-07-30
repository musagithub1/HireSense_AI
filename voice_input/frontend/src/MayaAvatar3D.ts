import * as THREE from "three";

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

const SKIN = 0xe6aa92;
const SKIN_LIGHT = 0xf0c0aa;
const SKIN_SHADOW = 0xc98270;
const HAIR = 0x21182b;
const BLAZER = 0x152344;
const BLAZER_LIGHT = 0x26375f;
const SHIRT = 0xf0efff;
const IRIS = 0x5b3f32;
const LIP = 0x9b5362;
const MOUTH = 0x421c2a;

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

function mesh(
  geometry: THREE.BufferGeometry,
  material: THREE.Material,
  {
    position = [0, 0, 0],
    rotation = [0, 0, 0],
    scale = [1, 1, 1],
    name = "",
  }: {
    position?: [number, number, number];
    rotation?: [number, number, number];
    scale?: [number, number, number];
    name?: string;
  } = {},
): THREE.Mesh {
  const value = new THREE.Mesh(geometry, material);
  value.position.set(...position);
  value.rotation.set(...rotation);
  value.scale.set(...scale);
  value.name = name;
  return value;
}

function makeShape(points: Array<[number, number]>): THREE.ShapeGeometry {
  const shape = new THREE.Shape();
  points.forEach(([x, y], index) => {
    if (index === 0) shape.moveTo(x, y);
    else shape.lineTo(x, y);
  });
  shape.closePath();
  return new THREE.ShapeGeometry(shape);
}

function makeUpperLip(): THREE.ShapeGeometry {
  const shape = new THREE.Shape();
  shape.moveTo(-0.18, 0);
  shape.quadraticCurveTo(-0.095, 0.038, 0, 0.012);
  shape.quadraticCurveTo(0.095, 0.038, 0.18, 0);
  shape.quadraticCurveTo(0, -0.024, -0.18, 0);
  return new THREE.ShapeGeometry(shape);
}

function makeLowerLip(): THREE.ShapeGeometry {
  const shape = new THREE.Shape();
  shape.moveTo(-0.17, 0);
  shape.quadraticCurveTo(0, -0.047, 0.17, 0);
  shape.quadraticCurveTo(0, 0.016, -0.17, 0);
  return new THREE.ShapeGeometry(shape);
}

export class MayaAvatar3D {
  private readonly canvas: HTMLCanvasElement;
  private readonly onUnavailable: () => void;
  private readonly renderer: THREE.WebGLRenderer;
  private readonly scene = new THREE.Scene();
  private readonly camera = new THREE.PerspectiveCamera(31, 1, 0.1, 50);
  private readonly avatar = new THREE.Group();
  private readonly body = new THREE.Group();
  private readonly head = new THREE.Group();
  private readonly leftEye = new THREE.Group();
  private readonly rightEye = new THREE.Group();
  private readonly leftIris = new THREE.Group();
  private readonly rightIris = new THREE.Group();
  private readonly leftBrow: THREE.Mesh;
  private readonly rightBrow: THREE.Mesh;
  private readonly mouthCavity: THREE.Mesh;
  private readonly upperLip: THREE.Mesh;
  private readonly lowerLip: THREE.Mesh;
  private readonly thinkingDots = new THREE.Group();
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
  private gazeX = 0;
  private gazeY = 0;
  private cachedVoiceLevel = 0;
  private mouthOpen = 0;
  private mouthWidth = 1;
  private frameCount = 0;
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
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.12;

    this.camera.position.set(0, 0.12, 5.25);
    this.camera.lookAt(0, -0.08, 0);

    this.scene.add(this.avatar);
    this.avatar.add(this.body, this.head);

    this.addLighting();
    this.addBody();
    const faceParts = this.addHead();
    this.leftBrow = faceParts.leftBrow;
    this.rightBrow = faceParts.rightBrow;
    this.mouthCavity = faceParts.mouthCavity;
    this.upperLip = faceParts.upperLip;
    this.lowerLip = faceParts.lowerLip;

    this.avatar.position.y = -0.08;
    this.avatar.rotation.y = -0.015;

    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(canvas);
    canvas.addEventListener("pointermove", this.handlePointerMove);
    canvas.addEventListener("pointerleave", this.handlePointerLeave);
    canvas.addEventListener("webglcontextlost", this.handleContextLost);

    this.resize();
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
    this.canvas.removeEventListener("webglcontextlost", this.handleContextLost);
    disposeObject(this.scene);
    this.renderer.dispose();
    this.renderer.forceContextLoss();
  }

  private addLighting(): void {
    const ambient = new THREE.HemisphereLight(0xe9e5ff, 0x10182d, 2.45);
    this.scene.add(ambient);

    const key = new THREE.DirectionalLight(0xffddca, 4.2);
    key.position.set(-2.4, 3.1, 4.2);
    this.scene.add(key);

    const fill = new THREE.PointLight(0x8d7cff, 16, 7.5, 2);
    fill.position.set(2.6, 1.5, 3);
    this.scene.add(fill);

    const rim = new THREE.DirectionalLight(0x55d8ff, 2.4);
    rim.position.set(2.8, 2.1, -2.5);
    this.scene.add(rim);
  }

  private addBody(): void {
    const blazerMaterial = new THREE.MeshStandardMaterial({
      color: BLAZER,
      roughness: 0.72,
      metalness: 0.04,
    });
    const blazerLightMaterial = new THREE.MeshStandardMaterial({
      color: BLAZER_LIGHT,
      roughness: 0.7,
    });
    const shirtMaterial = new THREE.MeshStandardMaterial({
      color: SHIRT,
      roughness: 0.72,
    });
    const skinMaterial = new THREE.MeshPhysicalMaterial({
      color: SKIN_SHADOW,
      roughness: 0.72,
      clearcoat: 0.025,
    });

    const torso = mesh(
      new THREE.SphereGeometry(1, 32, 22),
      blazerMaterial,
      {
        position: [0, -1.16, -0.03],
        scale: [1.34, 0.77, 0.56],
        name: "maya-torso",
      },
    );
    this.body.add(torso);

    const neck = mesh(
      new THREE.CylinderGeometry(0.23, 0.29, 0.53, 24),
      skinMaterial,
      {
        position: [0, -0.37, 0.03],
        name: "maya-neck",
      },
    );
    this.body.add(neck);

    const shirt = mesh(
      makeShape([
        [-0.34, 0.12],
        [0.34, 0.12],
        [0, -0.62],
      ]),
      shirtMaterial,
      {
        position: [0, -0.82, 0.51],
        name: "maya-shirt",
      },
    );
    this.body.add(shirt);

    const leftLapel = mesh(
      makeShape([
        [-0.02, 0.05],
        [-0.62, -0.06],
        [-0.32, -0.73],
        [0.05, -0.24],
      ]),
      blazerLightMaterial,
      {
        position: [-0.02, -0.67, 0.535],
        name: "maya-left-lapel",
      },
    );
    const rightLapel = mesh(
      makeShape([
        [0.02, 0.05],
        [0.62, -0.06],
        [0.32, -0.73],
        [-0.05, -0.24],
      ]),
      blazerLightMaterial,
      {
        position: [0.02, -0.67, 0.535],
        name: "maya-right-lapel",
      },
    );
    this.body.add(leftLapel, rightLapel);
  }

  private addHead(): {
    leftBrow: THREE.Mesh;
    rightBrow: THREE.Mesh;
    mouthCavity: THREE.Mesh;
    upperLip: THREE.Mesh;
    lowerLip: THREE.Mesh;
  } {
    const skinMaterial = new THREE.MeshPhysicalMaterial({
      color: SKIN,
      roughness: 0.61,
      metalness: 0,
      clearcoat: 0.035,
      clearcoatRoughness: 0.8,
    });
    const skinLightMaterial = new THREE.MeshPhysicalMaterial({
      color: SKIN_LIGHT,
      roughness: 0.64,
      clearcoat: 0.025,
    });
    const hairMaterial = new THREE.MeshStandardMaterial({
      color: HAIR,
      roughness: 0.68,
      metalness: 0.02,
    });
    const backHair = mesh(
      new THREE.SphereGeometry(1, 36, 30),
      hairMaterial,
      {
        position: [0, 0.56, -0.23],
        scale: [0.88, 1.18, 0.61],
        name: "maya-back-hair",
      },
    );
    this.head.add(backHair);

    const face = mesh(
      new THREE.SphereGeometry(1, 40, 34),
      skinMaterial,
      {
        position: [0, 0.58, 0.03],
        scale: [0.71, 0.92, 0.64],
        name: "maya-face",
      },
    );
    this.head.add(face);

    const leftEar = mesh(
      new THREE.SphereGeometry(0.16, 20, 16),
      skinMaterial,
      {
        position: [-0.72, 0.55, 0.01],
        scale: [0.5, 0.9, 0.45],
        name: "maya-left-ear",
      },
    );
    const rightEar = leftEar.clone();
    rightEar.position.x = 0.72;
    rightEar.name = "maya-right-ear";
    this.head.add(leftEar, rightEar);

    const hairCap = mesh(
      new THREE.SphereGeometry(
        1,
        38,
        22,
        0,
        Math.PI * 2,
        0,
        Math.PI * 0.47,
      ),
      hairMaterial,
      {
        position: [0, 0.76, 0.02],
        scale: [0.75, 0.93, 0.67],
        rotation: [0, 0, -0.04],
        name: "maya-hair-cap",
      },
    );
    this.head.add(hairCap);

    const sideGeometry = new THREE.CapsuleGeometry(0.13, 0.72, 8, 16);
    const leftHair = mesh(sideGeometry, hairMaterial, {
      position: [-0.69, 0.14, -0.02],
      rotation: [0.04, 0, -0.045],
      scale: [1, 1.34, 0.9],
      name: "maya-left-hair",
    });
    const rightHair = mesh(sideGeometry.clone(), hairMaterial, {
      position: [0.69, 0.13, -0.03],
      rotation: [-0.02, 0, 0.055],
      scale: [1, 1.36, 0.9],
      name: "maya-right-hair",
    });
    this.head.add(leftHair, rightHair);

    this.addEye(this.leftEye, this.leftIris, -0.245);
    this.addEye(this.rightEye, this.rightIris, 0.245);
    this.head.add(this.leftEye, this.rightEye);

    const browMaterial = new THREE.MeshStandardMaterial({
      color: 0x3c2430,
      roughness: 0.9,
    });
    const browGeometry = new THREE.CapsuleGeometry(0.019, 0.18, 5, 10);
    const leftBrow = mesh(browGeometry, browMaterial, {
      position: [-0.255, 0.83, 0.63],
      rotation: [0, 0, Math.PI / 2 + 0.09],
      name: "maya-left-brow",
    });
    const rightBrow = mesh(browGeometry.clone(), browMaterial, {
      position: [0.255, 0.83, 0.63],
      rotation: [0, 0, Math.PI / 2 - 0.09],
      name: "maya-right-brow",
    });
    this.head.add(leftBrow, rightBrow);

    const noseBridge = mesh(
      new THREE.SphereGeometry(0.105, 20, 16),
      skinLightMaterial,
      {
        position: [0, 0.45, 0.65],
        scale: [0.38, 1.02, 0.4],
        name: "maya-nose-bridge",
      },
    );
    const noseTip = mesh(
      new THREE.SphereGeometry(0.08, 20, 16),
      skinLightMaterial,
      {
        position: [0, 0.35, 0.688],
        scale: [0.75, 0.52, 0.46],
        name: "maya-nose-tip",
      },
    );
    this.head.add(noseBridge, noseTip);

    const mouthMaterial = new THREE.MeshStandardMaterial({
      color: MOUTH,
      roughness: 0.8,
    });
    const lipMaterial = new THREE.MeshPhysicalMaterial({
      color: LIP,
      roughness: 0.64,
      clearcoat: 0.08,
    });
    const mouthCavity = mesh(
      new THREE.CircleGeometry(0.16, 32),
      mouthMaterial,
      {
        position: [0, 0.075, 0.657],
        scale: [1.02, 0.11, 1],
        name: "maya-mouth",
      },
    );
    const upperLip = mesh(makeUpperLip(), lipMaterial, {
      position: [0, 0.094, 0.671],
      scale: [1, 1, 1],
      name: "maya-upper-lip",
    });
    const lowerLip = mesh(makeLowerLip(), lipMaterial, {
      position: [0, 0.057, 0.672],
      scale: [1, 1, 1],
      name: "maya-lower-lip",
    });
    this.head.add(mouthCavity, upperLip, lowerLip);

    const cheekMaterial = new THREE.MeshBasicMaterial({
      color: 0xe98787,
      transparent: true,
      opacity: 0.09,
      depthWrite: false,
    });
    const cheekGeometry = new THREE.SphereGeometry(0.14, 16, 12);
    const leftCheek = mesh(cheekGeometry, cheekMaterial, {
      position: [-0.37, 0.26, 0.6],
      scale: [1.25, 0.48, 0.18],
    });
    const rightCheek = leftCheek.clone();
    rightCheek.position.x = 0.37;
    this.head.add(leftCheek, rightCheek);

    const dotMaterial = new THREE.MeshBasicMaterial({
      color: 0xa996ff,
      transparent: true,
      opacity: 0,
    });
    for (let index = 0; index < 3; index += 1) {
      const dot = mesh(
        new THREE.SphereGeometry(0.045, 14, 10),
        dotMaterial.clone(),
        {
          position: [0.72 + index * 0.13, 1.25 + index * 0.08, 0.15],
          name: `maya-thinking-dot-${index + 1}`,
        },
      );
      this.thinkingDots.add(dot);
    }
    this.head.add(this.thinkingDots);

    return {
      leftBrow,
      rightBrow,
      mouthCavity,
      upperLip,
      lowerLip,
    };
  }

  private addEye(
    eye: THREE.Group,
    iris: THREE.Group,
    x: number,
  ): void {
    const eyeMaterial = new THREE.MeshPhysicalMaterial({
      color: 0xfffaf5,
      roughness: 0.4,
      clearcoat: 0.12,
    });
    const irisMaterial = new THREE.MeshPhysicalMaterial({
      color: IRIS,
      roughness: 0.38,
      clearcoat: 0.22,
    });
    const pupilMaterial = new THREE.MeshBasicMaterial({ color: 0x17111c });
    const highlightMaterial = new THREE.MeshBasicMaterial({ color: 0xffffff });

    const white = mesh(
      new THREE.SphereGeometry(0.082, 24, 18),
      eyeMaterial,
      {
        scale: [1.28, 0.58, 0.36],
        name: x < 0 ? "maya-left-eye" : "maya-right-eye",
      },
    );
    const irisDisc = mesh(
      new THREE.SphereGeometry(0.032, 20, 14),
      irisMaterial,
      {
        position: [0, 0, 0.065],
        scale: [1, 1, 0.28],
      },
    );
    const pupil = mesh(
      new THREE.SphereGeometry(0.014, 16, 12),
      pupilMaterial,
      {
        position: [0, 0, 0.078],
        scale: [1, 1, 0.24],
      },
    );
    const highlight = mesh(
      new THREE.SphereGeometry(0.005, 12, 8),
      highlightMaterial,
      {
        position: [-0.009, 0.009, 0.087],
      },
    );

    iris.add(irisDisc, pupil, highlight);
    eye.add(white, iris);
    eye.position.set(x, 0.66, 0.655);
  }

  private resize(): void {
    const width = Math.max(1, this.canvas.clientWidth);
    const height = Math.max(1, this.canvas.clientHeight);
    const pixelRatio = Math.min(
      window.devicePixelRatio || 1,
      width < 220 ? 1.15 : 1.55,
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

  private voiceLevel(): number {
    if (this.frameCount % 6 !== 0) return this.cachedVoiceLevel;
    const host = this.canvas.closest(".interview-avatar");
    if (!(host instanceof HTMLElement)) return this.cachedVoiceLevel;
    const value = Number.parseFloat(
      window
        .getComputedStyle(host)
        .getPropertyValue("--voice-level")
        .trim(),
    );
    this.cachedVoiceLevel = Number.isFinite(value) ? clamp(value) : 0;
    return this.cachedVoiceLevel;
  }

  private blinkAmount(elapsed: number): number {
    if (this.reducedMotion || this.state === "paused") return 0;
    const phase = (elapsed + 0.7) % 5.4;
    if (phase < 0.15) return Math.sin((phase / 0.15) * Math.PI);
    if (phase > 0.29 && phase < 0.39 && elapsed % 16 < 5.4) {
      return Math.sin(((phase - 0.29) / 0.1) * Math.PI) * 0.72;
    }
    return 0;
  }

  private visemeShape(elapsed: number): {
    open: number;
    width: number;
  } {
    if (this.state !== "speaking") return { open: 0, width: 1 };

    const procedural =
      0.22 +
      Math.abs(
        Math.sin(elapsed * 8.6 + Math.sin(elapsed * 2.2) * 1.7),
      ) *
        0.78;
    const intensity = Math.max(0.32, this.visemeIntensity);
    const shapes: Record<MayaViseme, { open: number; width: number }> = {
      rest: { open: 0.45, width: 1 },
      A: { open: 1, width: 1.04 },
      E: { open: 0.48, width: 1.3 },
      I: { open: 0.34, width: 1.24 },
      O: { open: 0.82, width: 0.76 },
      U: { open: 0.57, width: 0.66 },
    };
    const shape = shapes[this.viseme] ?? shapes.rest;
    return {
      open: clamp(shape.open * procedural * intensity, 0.08, 1),
      width: THREE.MathUtils.lerp(1, shape.width, intensity),
    };
  }

  private updateExpression(elapsed: number, delta: number): void {
    const motion = this.reducedMotion ? 0 : 1;
    const voiceLevel = this.state === "listening" ? this.voiceLevel() : 0;
    const breathe = Math.sin(elapsed * 1.28) * 0.012 * motion;
    this.body.scale.y = 1 + breathe;
    this.body.position.y = breathe * -0.2;

    let targetHeadX = 0;
    let targetHeadY = this.pointerX * 0.035;
    let targetHeadZ = 0;
    let targetGazeX = this.pointerX * 0.034;
    let targetGazeY = this.pointerY * 0.019;

    if (this.state === "speaking") {
      targetHeadX = Math.sin(elapsed * 1.37) * 0.018 * motion;
      targetHeadY += Math.sin(elapsed * 0.73) * 0.027 * motion;
      targetHeadZ = Math.sin(elapsed * 0.96) * 0.012 * motion;
    } else if (this.state === "listening") {
      const nodPhase = elapsed % 5.1;
      const nod =
        nodPhase > 3.9 && nodPhase < 4.55
          ? Math.sin(((nodPhase - 3.9) / 0.65) * Math.PI) * 0.052
          : 0;
      targetHeadX = (nod + voiceLevel * 0.018) * motion;
      targetGazeX *= 0.45;
      targetGazeY *= 0.45;
    } else if (this.state === "processing") {
      targetHeadX = -0.025 * motion;
      targetHeadY = 0.075 * motion;
      targetGazeX = 0.048 * motion;
      targetGazeY = 0.026 * motion;
    } else if (this.state === "error" || this.state === "offline") {
      targetHeadX = 0.025;
      targetHeadZ = -0.022;
    }

    this.head.rotation.x = damp(
      this.head.rotation.x,
      targetHeadX,
      4.2,
      delta,
    );
    this.head.rotation.y = damp(
      this.head.rotation.y,
      targetHeadY,
      4.2,
      delta,
    );
    this.head.rotation.z = damp(
      this.head.rotation.z,
      targetHeadZ,
      4.2,
      delta,
    );

    this.gazeX = damp(this.gazeX, targetGazeX, 7.5, delta);
    this.gazeY = damp(this.gazeY, targetGazeY, 7.5, delta);
    for (const iris of [this.leftIris, this.rightIris]) {
      iris.position.x = this.gazeX;
      iris.position.y = this.gazeY;
    }

    const blink = this.blinkAmount(elapsed);
    const eyeScale = Math.max(0.07, 1 - blink * 0.93);
    this.leftEye.scale.y = eyeScale;
    this.rightEye.scale.y = eyeScale;

    const viseme = this.visemeShape(elapsed);
    this.mouthOpen = damp(this.mouthOpen, viseme.open, 16, delta);
    this.mouthWidth = damp(this.mouthWidth, viseme.width, 13, delta);
    this.visemeIntensity = Math.max(
      this.state === "speaking" ? 0.28 : 0,
      this.visemeIntensity - delta * 1.65,
    );

    const supportiveSmile = this.supportMode ? 0.012 : 0;
    const openHeight = 0.11 + this.mouthOpen * 0.62;
    this.mouthCavity.scale.set(
      1.02 * this.mouthWidth,
      openHeight,
      1,
    );
    this.upperLip.position.y =
      0.095 + this.mouthOpen * 0.022 + supportiveSmile;
    this.lowerLip.position.y =
      0.055 - this.mouthOpen * 0.048 + supportiveSmile;
    this.upperLip.scale.x = this.mouthWidth;
    this.lowerLip.scale.x = this.mouthWidth;

    const supportiveBrow = this.supportMode ? -0.025 : 0;
    this.leftBrow.rotation.z = damp(
      this.leftBrow.rotation.z,
      Math.PI / 2 + 0.09 + supportiveBrow,
      4.5,
      delta,
    );
    this.rightBrow.rotation.z = damp(
      this.rightBrow.rotation.z,
      Math.PI / 2 - 0.09 - supportiveBrow,
      4.5,
      delta,
    );

    this.thinkingDots.children.forEach((dot, index) => {
      const material = (dot as THREE.Mesh).material as THREE.MeshBasicMaterial;
      const thinking = this.state === "processing";
      material.opacity = damp(
        material.opacity,
        thinking
          ? 0.28 +
              Math.abs(Math.sin(elapsed * 3.5 - index * 0.75)) * 0.72
          : 0,
        7,
        delta,
      );
      dot.position.y =
        1.25 +
        index * 0.08 +
        (thinking ? Math.sin(elapsed * 3.5 - index * 0.75) * 0.035 : 0);
    });

    const paused = ["paused", "offline", "error"].includes(this.state);
    this.avatar.rotation.y = damp(
      this.avatar.rotation.y,
      paused ? -0.04 : -0.015,
      3,
      delta,
    );
    this.avatar.position.y = -0.08 + Math.sin(elapsed * 1.05) * 0.006 * motion;
  }

  private animate = (): void => {
    if (this.destroyed) return;
    const delta = Math.min(0.05, this.clock.getDelta());
    const elapsed = this.clock.elapsedTime;
    this.frameCount += 1;
    this.updateExpression(elapsed, delta);
    this.renderer.render(this.scene, this.camera);
    this.animationFrame = window.requestAnimationFrame(this.animate);
  };
}
