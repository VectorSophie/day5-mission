import * as THREE from "https://esm.sh/three@0.160.0";
import { OrbitControls } from "https://esm.sh/three@0.160.0/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "https://esm.sh/three@0.160.0/examples/jsm/loaders/GLTFLoader.js";
import {
  VRMExpressionPresetName,
  VRMLoaderPlugin,
  VRMUtils,
} from "https://esm.sh/@pixiv/three-vrm@2.1.2";

const MODEL_URL = "/model/lumi.vrm";

function setStatus(message) {
  const status = document.getElementById("lumi-avatar-status");
  if (status) {
    status.textContent = message;
  }
}

function resolveAudioUrl(audioUrl) {
  if (!audioUrl) return null;
  if (audioUrl.startsWith("http://") || audioUrl.startsWith("https://")) return audioUrl;
  return `${window.location.origin}${audioUrl}`;
}

function mapPhonemeToPreset(phoneme) {
  if (phoneme === "a") return VRMExpressionPresetName.Aa;
  if (phoneme === "i") return VRMExpressionPresetName.Ih;
  if (phoneme === "u") return VRMExpressionPresetName.Ou;
  if (phoneme === "e") return VRMExpressionPresetName.Ee;
  return VRMExpressionPresetName.Oh;
}

function applyEmotion(vrm, emotion) {
  if (!vrm || !vrm.expressionManager) return;
  const manager = vrm.expressionManager;
  manager.setValue(VRMExpressionPresetName.Happy, 0);
  manager.setValue(VRMExpressionPresetName.Angry, 0);
  manager.setValue(VRMExpressionPresetName.Sad, 0);

  if (emotion === "happy") manager.setValue(VRMExpressionPresetName.Happy, 0.8);
  if (emotion === "angry") manager.setValue(VRMExpressionPresetName.Angry, 0.7);
  if (emotion === "sad") manager.setValue(VRMExpressionPresetName.Sad, 0.7);
}

function clearLip(vrm) {
  if (!vrm || !vrm.expressionManager) return;
  const manager = vrm.expressionManager;
  manager.setValue(VRMExpressionPresetName.Aa, 0);
  manager.setValue(VRMExpressionPresetName.Ih, 0);
  manager.setValue(VRMExpressionPresetName.Ou, 0);
  manager.setValue(VRMExpressionPresetName.Ee, 0);
  manager.setValue(VRMExpressionPresetName.Oh, 0);
}

function playLipSync(vrm, visemes) {
  if (!vrm || !vrm.expressionManager || !Array.isArray(visemes) || visemes.length === 0) return;
  clearLip(vrm);
  for (const viseme of visemes) {
    const start = Math.max(0, Number(viseme.start || 0) * 1000);
    const end = Math.max(start + 40, Number(viseme.end || 0) * 1000);
    const preset = mapPhonemeToPreset(viseme.phoneme);
    window.setTimeout(() => {
      vrm.expressionManager.setValue(preset, 0.9);
    }, start);
    window.setTimeout(() => {
      vrm.expressionManager.setValue(preset, 0);
    }, end);
  }
}

async function initAvatar() {
  if (window.__lumiAvatarBooted) return;
  window.__lumiAvatarBooted = true;

  const canvas = document.getElementById("lumi-avatar-canvas");
  if (!canvas) {
    window.__lumiAvatarBooted = false;
    window.setTimeout(() => {
      void initAvatar();
    }, 500);
    return;
  }

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 20);
  camera.position.set(0, 1.35, 1.5);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 1.3, 0);
  controls.enablePan = false;
  controls.minDistance = 0.7;
  controls.maxDistance = 3.0;
  controls.update();

  scene.add(new THREE.HemisphereLight(0xffffff, 0x222244, 1.3));
  const dir = new THREE.DirectionalLight(0xffffff, 1.3);
  dir.position.set(1, 2, 1);
  scene.add(dir);

  function resize() {
    const rect = canvas.getBoundingClientRect();
    const w = Math.max(320, Math.floor(rect.width));
    const h = Math.max(420, Math.floor(rect.height));
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }

  const loader = new GLTFLoader();
  loader.register((parser) => new VRMLoaderPlugin(parser));

  setStatus("Loading model...");
  let currentVrm = null;
  try {
    const gltf = await loader.loadAsync(MODEL_URL);
    currentVrm = gltf.userData.vrm;
    VRMUtils.rotateVRM0(currentVrm);
    currentVrm.scene.position.set(0, 0, 0);
    scene.add(currentVrm.scene);
    setStatus("Ready");
  } catch (error) {
    console.error(error);
    setStatus("Model load failed. Check /model/lumi.vrm");
  }

  function render() {
    requestAnimationFrame(render);
    resize();
    if (currentVrm) {
      currentVrm.update(1 / 60);
    }
    renderer.render(scene, camera);
  }
  render();

  let previousPayload = "";
  window.setInterval(() => {
    const input = document.querySelector("#avatar-payload textarea, #avatar-payload input");
    if (!input) return;
    const raw = input.value || "";
    if (!raw || raw === previousPayload) return;
    previousPayload = raw;

    try {
      const payload = JSON.parse(raw);
      applyEmotion(currentVrm, payload.emotion || "neutral");
      playLipSync(currentVrm, payload.visemes || []);
      const audioSrc = resolveAudioUrl(payload.audio_url);
      if (audioSrc) {
        const audio = new Audio(audioSrc);
        audio.play().catch(() => null);
      }
      setStatus(payload.text ? `Speaking: ${payload.text.slice(0, 22)}...` : "Speaking");
    } catch {
      setStatus("Ready");
    }
  }, 250);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    void initAvatar();
  });
} else {
  void initAvatar();
}

const observer = new MutationObserver(() => {
  if (document.getElementById("lumi-avatar-canvas") && !window.__lumiAvatarBooted) {
    void initAvatar();
  }
});
observer.observe(document.documentElement, { childList: true, subtree: true });
