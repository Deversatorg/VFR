import { useRef, useEffect, useMemo, useState } from 'react';
import { useFrame, createPortal } from '@react-three/fiber';
import { Float, MeshDistortMaterial, useGLTF, useAnimations, Html } from '@react-three/drei';
import * as THREE from 'three';
import { ErrorBoundary, type FallbackProps } from 'react-error-boundary';

// ─── Public API ───────────────────────────────────────────────────────────────

export interface AvatarViewerProps {
    modelUrl?: string | null;
    height?: number;
    weight?: number;
    bodyType?: string;
    gender?: 'male' | 'female';
    animation?: 'idle' | 'walk' | 'run' | 'jump' | 'tpose';
    showShirt?: boolean;
    /** Override garment GLB. Defaults to /models/garments/t-shirt.glb */
    garmentUrl?: string;
}

// ─── Bone-name candidates (tried in order, first match wins) ─────────────────
const SPINE_BONE_CANDIDATES = [
    'mixamorig:Spine2',
    'mixamorig:Spine1',
    'mixamorig:Spine',
    'Spine2',
    'Spine1',
    'Spine',
    'Chest',
    'chest',
    'spine2',
    'spine1',
    'spine',
];

/**
 * Walk an Object3D tree and return the first bone whose name is in the
 * candidates list, in candidate priority order.
 */
function findSpineBone(root: THREE.Object3D): THREE.Bone | null {
    const found = new Map<string, THREE.Bone>();

    root.traverse((node) => {
        if ((node as THREE.Bone).isBone) {
            const bone = node as THREE.Bone;
            if (SPINE_BONE_CANDIDATES.includes(bone.name) && !found.has(bone.name)) {
                found.set(bone.name, bone);
            }
        }
    });

    for (const name of SPINE_BONE_CANDIDATES) {
        const bone = found.get(name);
        if (bone) return bone;
    }

    // Last resort: any bone with "spine" or "chest" in the name
    let fallback: THREE.Bone | null = null;
    root.traverse((node) => {
        if (fallback) return;
        if ((node as THREE.Bone).isBone) {
            const lower = node.name.toLowerCase();
            if (lower.includes('spine') || lower.includes('chest')) {
                fallback = node as THREE.Bone;
            }
        }
    });

    return fallback;
}

// ─── Scale presets for the debug panel ───────────────────────────────────────
const SCALE_PRESETS = [0.001, 0.01, 0.1, 1, 10] as const;

// ─── Debug overlay (rendered via Html so it sits in DOM, not 3D space) ───────
function GarmentDebugPanel({
    scale,
    onScale,
    offsetY,
    onOffsetY,
    offsetX,
    onOffsetX,
    offsetZ,
    onOffsetZ,
    boneName,
}: {
    scale: number;
    onScale: (v: number) => void;
    offsetY: number;
    onOffsetY: (v: number) => void;
    offsetX: number;
    onOffsetX: (v: number) => void;
    offsetZ: number;
    onOffsetZ: (v: number) => void;
    boneName: string;
}) {
    const btn = (label: string, active: boolean, onClick: () => void) => (
        <button
            key={label}
            onClick={onClick}
            style={{
                padding: '3px 8px',
                fontSize: 11,
                cursor: 'pointer',
                borderRadius: 6,
                border: active ? '1px solid #6366f1' : '1px solid #374151',
                background: active ? '#312e81' : '#111827',
                color: active ? '#a5b4fc' : '#9ca3af',
                marginRight: 4,
            }}
        >
            {label}
        </button>
    );

    const nudge = (setter: (v: number) => void, cur: number, delta: number) =>
        () => setter(parseFloat((cur + delta).toFixed(3)));

    return (
        <Html
            position={[0, 0, 0]}
            style={{ pointerEvents: 'auto', userSelect: 'none' }}
            prepend
            zIndexRange={[100, 0]}
        >
            <div style={{
                position: 'fixed',
                top: 12,
                right: 12,
                background: 'rgba(9,9,11,0.92)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 14,
                padding: '14px 16px',
                minWidth: 250,
                backdropFilter: 'blur(12px)',
                fontFamily: 'monospace',
                color: '#e5e7eb',
                fontSize: 12,
                boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
            }}>
                <div style={{ color: '#6366f1', fontWeight: 700, marginBottom: 10, letterSpacing: 1 }}>
                    👕 GARMENT DEBUG
                </div>

                <div style={{ marginBottom: 8 }}>
                    <span style={{ color: '#6b7280', fontSize: 10 }}>BONE: </span>
                    <span style={{ color: '#34d399' }}>{boneName || '⚠ not found'}</span>
                </div>

                {/* Scale */}
                <div style={{ marginBottom: 10 }}>
                    <div style={{ color: '#9ca3af', marginBottom: 4, fontSize: 10, letterSpacing: 1 }}>
                        SCALE: <span style={{ color: '#f9fafb' }}>{scale}</span>
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                        {SCALE_PRESETS.map(p => btn(`×${p}`, scale === p, () => onScale(p)))}
                    </div>
                    <input
                        type="range"
                        min={-4} max={2} step={0.01}
                        value={Math.log10(scale)}
                        onChange={e => onScale(parseFloat(Math.pow(10, +e.target.value).toPrecision(3)))}
                        style={{ width: '100%', marginTop: 6, accentColor: '#6366f1' }}
                    />
                </div>

                {/* Position Y */}
                <div style={{ marginBottom: 8 }}>
                    <div style={{ color: '#9ca3af', marginBottom: 4, fontSize: 10, letterSpacing: 1 }}>
                        OFFSET Y: <span style={{ color: '#f9fafb' }}>{offsetY.toFixed(3)}</span>
                    </div>
                    <div style={{ display: 'flex', gap: 4 }}>
                        {[-0.1, -0.01, 0, 0.01, 0.1].map(d => btn(
                            d === 0 ? 'reset' : (d > 0 ? `+${d}` : `${d}`),
                            d === 0 && offsetY === 0,
                            d === 0 ? () => onOffsetY(0) : nudge(onOffsetY, offsetY, d)
                        ))}
                    </div>
                </div>

                {/* Position X */}
                <div style={{ marginBottom: 8 }}>
                    <div style={{ color: '#9ca3af', marginBottom: 4, fontSize: 10, letterSpacing: 1 }}>
                        OFFSET X: <span style={{ color: '#f9fafb' }}>{offsetX.toFixed(3)}</span>
                    </div>
                    <div style={{ display: 'flex', gap: 4 }}>
                        {[-0.1, -0.01, 0, 0.01, 0.1].map(d => btn(
                            d === 0 ? 'reset' : (d > 0 ? `+${d}` : `${d}`),
                            d === 0 && offsetX === 0,
                            d === 0 ? () => onOffsetX(0) : nudge(onOffsetX, offsetX, d)
                        ))}
                    </div>
                </div>

                {/* Position Z */}
                <div style={{ marginBottom: 4 }}>
                    <div style={{ color: '#9ca3af', marginBottom: 4, fontSize: 10, letterSpacing: 1 }}>
                        OFFSET Z: <span style={{ color: '#f9fafb' }}>{offsetZ.toFixed(3)}</span>
                    </div>
                    <div style={{ display: 'flex', gap: 4 }}>
                        {[-0.1, -0.01, 0, 0.01, 0.1].map(d => btn(
                            d === 0 ? 'reset' : (d > 0 ? `+${d}` : `${d}`),
                            d === 0 && offsetZ === 0,
                            d === 0 ? () => onOffsetZ(0) : nudge(onOffsetZ, offsetZ, d)
                        ))}
                    </div>
                </div>
            </div>
        </Html>
    );
}

// ─── Placeholder (no model URL yet) ──────────────────────────────────────────
function PlaceholderAvatar() {
    const meshRef = useRef<THREE.Mesh>(null);
    useFrame((_, delta) => {
        if (meshRef.current) meshRef.current.rotation.y += delta * 0.1;
    });
    return (
        <Float speed={1.5} rotationIntensity={0.5} floatIntensity={1}>
            <mesh ref={meshRef} scale={1.2}>
                <capsuleGeometry args={[0.5, 1.5, 4, 16]} />
                <MeshDistortMaterial
                    color="#4F46E5" attach="material"
                    distort={0.2} speed={2} roughness={0.2} metalness={0.8} wireframe
                />
            </mesh>
            <mesh position={[0, 1.2, 0]}>
                <sphereGeometry args={[0.4, 32, 32]} />
                <meshStandardMaterial color="#818cf8" roughness={0.3} metalness={0.8} />
            </mesh>
        </Float>
    );
}

// ─── Loaded Avatar + Garment attachment ───────────────────────────────────────
function LoadedAvatar({
    url,
    garmentUrl,
    height = 170,
    weight = 70,
    bodyType = 'regular',
    animation = 'idle',
    showShirt = false,
}: {
    url: string;
    garmentUrl: string;
    height: number;
    weight: number;
    bodyType: string;
    animation?: string;
    showShirt?: boolean;
}) {
    // Explicit, unambiguous naming — avatarGltf = avatar body, garmentGltf = clothing
    const avatarGltf = useGLTF(url);
    const garmentGltf = useGLTF(garmentUrl);

    const { actions, names } = useAnimations(avatarGltf.animations, avatarGltf.scene);

    // Debug state (only matters when showShirt is true)
    const [garmentScale, setGarmentScale] = useState(1);
    const [offsetY, setOffsetY] = useState(0);
    const [offsetX, setOffsetX] = useState(0);
    const [offsetZ, setOffsetZ] = useState(0);

    // ── 1. Find spine bone ─────────────────────────────────────────────────
    const spineBone = useMemo(() => findSpineBone(avatarGltf.scene), [avatarGltf.scene]);

    // ── 2. Animation crossfade ─────────────────────────────────────────────
    useEffect(() => {
        if (!actions) return;
        Object.values(actions).forEach(a => a?.fadeOut(0.4));
        const target = actions[animation] ?? actions[names[0]];
        target?.reset().fadeIn(0.4).play();
    }, [animation, actions, names]);

    // ── 3. Morph targets ───────────────────────────────────────────────────
    useEffect(() => {
        avatarGltf.scene.traverse((child) => {
            const mesh = child as THREE.Mesh;
            if (!mesh.isMesh || !mesh.morphTargetDictionary || !mesh.morphTargetInfluences) return;

            const set = (key: string, val: number) => {
                const idx = mesh.morphTargetDictionary![key];
                if (idx !== undefined) mesh.morphTargetInfluences![idx] = val;
            };
            set('Fat', Math.min(1, Math.max(0, (weight - 70) / 50)));
            set('Muscular', bodyType === 'athletic' ? 1 : 0);
            set('Tall', Math.min(1, Math.max(0, (height - 170) / 30)));
        });
    }, [avatarGltf.scene, height, weight, bodyType]);

    // ── 4. Clone ONLY the garment scene ───────────────────────────────────
    // CRITICAL: garmentGltf.scene MUST be a different object from avatarGltf.scene.
    // If somehow the same URL is returned (cache collision), log the error and
    // render a bright diagnostic sphere so the bug is immediately visible.
    const garmentClone = useMemo(() => {
        if (garmentGltf.scene === avatarGltf.scene) {
            // This should never happen — signals a URL or caching bug.
            console.error(
                '[AvatarViewer] FATAL: garmentGltf.scene is the SAME object as avatarGltf.scene!',
                '\n  avatar URL:', url,
                '\n  garment URL:', garmentUrl,
            );
            // Return an empty group; the diagnostic sphere below will render instead
            return new THREE.Group();
        }
        console.info(
            '[AvatarViewer] Cloning garment scene:',
            garmentUrl,
            '— uuid:', garmentGltf.scene.uuid,
            '(avatar uuid:', avatarGltf.scene.uuid + ')'
        );
        return garmentGltf.scene.clone(true);
    }, [garmentGltf.scene, avatarGltf.scene, url, garmentUrl]);

    // Whether the garment loaded as a distinct object
    const garmentIsBroken = garmentGltf.scene === avatarGltf.scene;

    // Stamp every mesh in the garment so it's always visible (wireframe
    // overlay lets us see it even when textures/scale are wrong).
    useEffect(() => {
        garmentClone.traverse((node) => {
            const mesh = node as THREE.Mesh;
            if (!mesh.isMesh) return;
            mesh.castShadow = true;
            mesh.receiveShadow = false;
            // Ensure depthWrite is on so the shirt isn't invisible
            if (Array.isArray(mesh.material)) {
                mesh.material.forEach(m => { (m as THREE.MeshStandardMaterial).depthWrite = true; });
            } else {
                (mesh.material as THREE.MeshStandardMaterial).depthWrite = true;
            }
        });
    }, [garmentClone]);

    return (
        <>
            <primitive object={avatarGltf.scene} />

            {showShirt && (() => {
                // If garmentGltf.scene === avatarGltf.scene (cache collision / wrong URL),
                // render a bright red wireframe sphere so the bug is immediately visible.
                const garmentContent = garmentIsBroken ? (
                    <mesh>
                        <sphereGeometry args={[0.15, 16, 16]} />
                        <meshBasicMaterial color="#ff0000" wireframe />
                    </mesh>
                ) : (
                    <group scale={garmentScale} position={[offsetX, offsetY, offsetZ]}>
                        <primitive object={garmentClone} />
                    </group>
                );

                return (
                    <>
                        {spineBone
                            ? createPortal(garmentContent, spineBone)
                            : garmentContent
                        }
                        <GarmentDebugPanel
                            scale={garmentScale} onScale={setGarmentScale}
                            offsetY={offsetY} onOffsetY={setOffsetY}
                            offsetX={offsetX} onOffsetX={setOffsetX}
                            offsetZ={offsetZ} onOffsetZ={setOffsetZ}
                            boneName={spineBone?.name ?? ''}
                        />
                    </>
                );
            })()}
        </>
    );
}

// ─── Error fallback ───────────────────────────────────────────────────────────
function AvatarErrorFallback({ error }: FallbackProps) {
    console.error('[AvatarViewer] GLB load error:', error);
    return (
        <mesh scale={1.2}>
            <capsuleGeometry args={[0.5, 1.5, 4, 32]} />
            <meshStandardMaterial color="#ef4444" roughness={0.4} metalness={0.1} />
        </mesh>
    );
}

// ─── Public component ─────────────────────────────────────────────────────────
export default function AvatarViewer({
    modelUrl,
    height,
    weight,
    bodyType,
    animation,
    showShirt,
    garmentUrl = '/models/garments/t-shirt.glb',
}: AvatarViewerProps) {
    return (
        <group position={[0, -0.5, 0]}>
            {modelUrl ? (
                <ErrorBoundary FallbackComponent={AvatarErrorFallback}>
                    <LoadedAvatar
                        url={modelUrl}
                        garmentUrl={garmentUrl}
                        height={height ?? 170}
                        weight={weight ?? 70}
                        bodyType={bodyType ?? 'regular'}
                        animation={animation}
                        showShirt={showShirt}
                    />
                </ErrorBoundary>
            ) : (
                <PlaceholderAvatar />
            )}
        </group>
    );
}

// Pre-warm GLTF cache
useGLTF.preload('/models/Male.glb');
useGLTF.preload('/models/Female.glb');
useGLTF.preload('/models/garments/t-shirt.glb');
