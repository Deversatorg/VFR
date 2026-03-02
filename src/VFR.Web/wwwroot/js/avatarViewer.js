// VFR Three.js Avatar Viewer
// Loads a .glb model via GLTFLoader with orbit controls and studio lighting.

import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.163.0/build/three.module.js';
import { GLTFLoader } from 'https://cdn.jsdelivr.net/npm/three@0.163.0/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'https://cdn.jsdelivr.net/npm/three@0.163.0/examples/jsm/controls/OrbitControls.js';
import { RGBELoader } from 'https://cdn.jsdelivr.net/npm/three@0.163.0/examples/jsm/loaders/RGBELoader.js';

let renderer, scene, camera, controls, currentModel;

window.avatarViewer = {

    init(canvas) {
        if (renderer) return;

        // Renderer
        renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.2;
        renderer.outputColorSpace = THREE.SRGBColorSpace;
        renderer.shadowMap.enabled = true;

        // Scene
        scene = new THREE.Scene();
        scene.background = new THREE.Color(0x111827);

        // Camera
        const w = canvas.clientWidth || 600;
        const h = canvas.clientHeight || 700;
        camera = new THREE.PerspectiveCamera(45, w / h, 0.01, 100);
        camera.position.set(0, 1.4, 2.8);

        // Controls
        controls = new OrbitControls(camera, canvas);
        controls.target.set(0, 0.9, 0);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.minDistance = 0.8;
        controls.maxDistance = 5;

        // Lights
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
        scene.add(ambientLight);

        const keyLight = new THREE.DirectionalLight(0xfff5e6, 2.5);
        keyLight.position.set(1.5, 3, 2);
        keyLight.castShadow = true;
        scene.add(keyLight);

        const fillLight = new THREE.DirectionalLight(0xe0f0ff, 0.8);
        fillLight.position.set(-2, 1, -1);
        scene.add(fillLight);

        const rimLight = new THREE.DirectionalLight(0xffffff, 0.5);
        rimLight.position.set(0, 3, -3);
        scene.add(rimLight);

        // Floor grid
        const grid = new THREE.GridHelper(4, 20, 0x374151, 0x1f2937);
        grid.position.y = -0.01;
        scene.add(grid);

        // Resize handler
        const resize = () => {
            const w = canvas.clientWidth;
            const h = canvas.clientHeight;
            renderer.setSize(w, h, false);
            camera.aspect = w / h;
            camera.updateProjectionMatrix();
        };
        resize();
        window.addEventListener('resize', resize);

        // Render loop
        const animate = () => {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        };
        animate();
    },

    loadModel(url) {
        if (!scene) return;

        // Remove previous model
        if (currentModel) {
            scene.remove(currentModel);
            currentModel = null;
        }

        if (!url || url.includes('fallback') || url.includes('default')) {
            // Show placeholder humanoid silhouette
            this._addPlaceholder();
            return;
        }

        const loader = new GLTFLoader();
        loader.load(
            url,
            (gltf) => {
                currentModel = gltf.scene;

                // Centre & scale model to fit in view
                const box = new THREE.Box3().setFromObject(currentModel);
                const size = box.getSize(new THREE.Vector3());
                const scale = 1.8 / Math.max(size.x, size.y, size.z);
                currentModel.scale.setScalar(scale);
                const centre = box.getCenter(new THREE.Vector3());
                currentModel.position.sub(centre.multiplyScalar(scale));

                currentModel.castShadow = true;
                currentModel.receiveShadow = true;
                scene.add(currentModel);
            },
            undefined,
            (err) => {
                console.warn('GLTFLoader error, using placeholder:', err);
                this._addPlaceholder();
            }
        );
    },

    _addPlaceholder() {
        // Simple capsule as a placeholder humanoid
        const material = new THREE.MeshStandardMaterial({
            color: 0x6366f1,
            roughness: 0.4,
            metalness: 0.1,
            transparent: true,
            opacity: 0.85,
        });
        const group = new THREE.Group();

        // Body
        const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.22, 0.7, 8, 16), material);
        body.position.y = 0.9;
        group.add(body);

        // Head
        const head = new THREE.Mesh(new THREE.SphereGeometry(0.18, 16, 16), material);
        head.position.y = 1.65;
        group.add(head);

        // Arms
        const armMat = material.clone();
        [-0.36, 0.36].forEach(x => {
            const arm = new THREE.Mesh(new THREE.CapsuleGeometry(0.07, 0.52, 4, 8), armMat);
            arm.position.set(x, 0.88, 0);
            arm.rotation.z = x < 0 ? 0.3 : -0.3;
            group.add(arm);
        });

        // Legs
        [-0.16, 0.16].forEach(x => {
            const leg = new THREE.Mesh(new THREE.CapsuleGeometry(0.09, 0.6, 4, 8), material.clone());
            leg.position.set(x, 0.32, 0);
            group.add(leg);
        });

        currentModel = group;
        scene.add(currentModel);
    }
};
