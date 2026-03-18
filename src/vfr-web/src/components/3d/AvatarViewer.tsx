import { useRef, useEffect, useMemo, useState, Suspense } from 'react';
import { useFrame, createPortal } from '@react-three/fiber';
import { Float, MeshDistortMaterial, useGLTF, useAnimations, Html } from '@react-three/drei';
import * as THREE from 'three';
import { ErrorBoundary, type FallbackProps } from 'react-error-boundary';

// ─── Public Props ─────────────────────────────────────────────────────────────

export interface AvatarViewerProps {
    modelUrl?: string | null;
    height?: number;
    weight?: number;
    bodyType?: string;
    gender?: 'male' | 'female';
    animation?: 'idle' | 'walk' | 'run' | 'jump' | 'tpose';
    showShirt?: boolean;
    /** Override garment GLB path. Defaults to /models/garments/t-shirt.glb */
    garmentUrl?: string;
}

// ─── Bone search ──────────────────────────────────────────────────────────────

const SPINE_CANDIDATES = [
    'mixamorig:Spine2', 'mixamorig:Spine1', 'mixamorig:Spine',
    'Spine2', 'Spine1', 'Spine', 'Chest', 'chest', 
    'spine_3', 'spine_2', 'spine_1', 'spine', 'pelvis'
];

function findSpineAnchor(root: THREE.Object3D): THREE.Object3D | null {
    const boneMap = new Map<string, THREE.Object3D>();
    const nodeMap = new Map<string, THREE.Object3D>();
    root.traverse(node => {
        if (node.name && !nodeMap.has(node.name)) {
            nodeMap.set(node.name, node);
        }
        if ((node as THREE.Bone).isBone && !boneMap.has(node.name)) {
            boneMap.set(node.name, node);
        }
    });
    for (const name of SPINE_CANDIDATES) {
        const bone = boneMap.get(name);
        if (bone) return bone;
        const node = nodeMap.get(name);
        if (node) return node;
    }
    // Any named node with "spine", "chest", or "pelvis" in its name.
    let fallback: THREE.Object3D | null = null;
    root.traverse(node => {
        if (!fallback && node.name) {
            const l = node.name.toLowerCase();
            if (l.includes('spine') || l.includes('chest') || l.includes('pelvis')) {
                fallback = node;
            }
        }
    });
    return fallback;
}

// ─── Debug Panel ──────────────────────────────────────────────────────────────

interface TransformState {
    gScale: number;
    gPosX: number; gPosY: number; gPosZ: number;
    gRotX: number; gRotY: number; gRotZ: number;
}
interface TransformSetters {
    setGScale: (v: number) => void;
    setGPosX: (v: number) => void; setGPosY: (v: number) => void; setGPosZ: (v: number) => void;
    setGRotX: (v: number) => void; setGRotY: (v: number) => void; setGRotZ: (v: number) => void;
}

function DebugPanel({
    state, setters, boneName,
}: { state: TransformState; setters: TransformSetters; boneName: string }) {
    // ── tiny helpers ──
    const fmt = (v: number) => v.toFixed(3);
    const fmtD = (v: number) => `${(v * 180 / Math.PI).toFixed(1)}°`;
    const step = (set: (v: number) => void, cur: number, d: number) =>
        () => set(parseFloat((cur + d).toFixed(4)));
    const resetAll = () => {
        setters.setGScale(1);
        setters.setGPosX(0); setters.setGPosY(0); setters.setGPosZ(0);
        setters.setGRotX(0); setters.setGRotY(0); setters.setGRotZ(0);
    };

    // panel & row styles as plain objects for zero-dependency
    const panel: React.CSSProperties = {
        position: 'fixed', top: 12, right: 12,
        background: 'rgba(8,8,12,0.93)',
        border: '1px solid rgba(255,255,255,0.09)',
        borderRadius: 16, padding: '14px 16px', width: 280,
        backdropFilter: 'blur(14px)', fontFamily: 'monospace',
        fontSize: 11, color: '#e5e7eb', userSelect: 'none',
        boxShadow: '0 8px 40px rgba(0,0,0,0.7)',
        pointerEvents: 'auto',
    };
    const label: React.CSSProperties = {
        fontSize: 9, letterSpacing: 1.2, color: '#6b7280',
        textTransform: 'uppercase', marginBottom: 3,
    };
    const row: React.CSSProperties = {
        display: 'flex', alignItems: 'center', gap: 4, marginBottom: 8,
    };
    const val: React.CSSProperties = {
        minWidth: 52, textAlign: 'right', color: '#f9fafb', fontSize: 11,
    };
    const nudge = (label: string, onClick: () => void): React.ReactNode => (
        <button key={label} onClick={onClick} style={{
            padding: '2px 6px', fontSize: 10, cursor: 'pointer',
            borderRadius: 5, border: '1px solid #374151',
            background: '#111827', color: '#9ca3af',
            transition: 'background .15s',
        }}>{label}</button>
    );
    const slider = (
        value: number, set: (v: number) => void,
        min: number, max: number, step: number
    ) => (
        <input type="range" min={min} max={max} step={step} value={value}
            onChange={e => set(+e.target.value)}
            style={{ flex: 1, accentColor: '#6366f1', cursor: 'pointer' }}
        />
    );

    // ── sections ──
    type Row = { lbl: string; display: string; cur: number; set: (v: number) => void; min: number; max: number; step: number; delta: number };
    const ROWS: Row[] = [
        { lbl: 'Pos X', display: fmt(state.gPosX), cur: state.gPosX, set: setters.setGPosX, min: -2, max: 2, step: 0.001, delta: 0.01 },
        { lbl: 'Pos Y', display: fmt(state.gPosY), cur: state.gPosY, set: setters.setGPosY, min: -2, max: 2, step: 0.001, delta: 0.01 },
        { lbl: 'Pos Z', display: fmt(state.gPosZ), cur: state.gPosZ, set: setters.setGPosZ, min: -2, max: 2, step: 0.001, delta: 0.01 },
        { lbl: 'Rot X', display: fmtD(state.gRotX), cur: state.gRotX, set: setters.setGRotX, min: -Math.PI, max: Math.PI, step: 0.01, delta: Math.PI / 16 },
        { lbl: 'Rot Y', display: fmtD(state.gRotY), cur: state.gRotY, set: setters.setGRotY, min: -Math.PI, max: Math.PI, step: 0.01, delta: Math.PI / 16 },
        { lbl: 'Rot Z', display: fmtD(state.gRotZ), cur: state.gRotZ, set: setters.setGRotZ, min: -Math.PI, max: Math.PI, step: 0.01, delta: Math.PI / 16 },
    ];

    return (
        <Html prepend zIndexRange={[200, 0]} style={{ pointerEvents: 'none' }}>
            <div style={panel}>
                {/* Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                    <span style={{ color: '#818cf8', fontWeight: 700, fontSize: 12, letterSpacing: 1 }}>
                        👕 GARMENT DEBUG
                    </span>
                    <button onClick={resetAll} style={{
                        padding: '2px 8px', fontSize: 9, cursor: 'pointer',
                        borderRadius: 5, border: '1px solid #374151',
                        background: '#1f2937', color: '#9ca3af',
                    }}>RESET ALL</button>
                </div>

                {/* Bone name */}
                <div style={{ marginBottom: 10, color: '#6b7280', fontSize: 9 }}>
                    BONE:{' '}
                    <span style={{ color: boneName ? '#34d399' : '#f87171' }}>
                        {boneName || '⚠ not found'}
                    </span>
                </div>

                {/* Scale - log slider */}
                <div style={{ marginBottom: 10 }}>
                    <div style={label}>Scale <span style={{ color: '#f9fafb' }}>{state.gScale}</span></div>
                    <div style={row}>
                        {[0.001, 0.01, 0.1, 1, 10].map(p =>
                            <button key={p} onClick={() => setters.setGScale(p)} style={{
                                padding: '2px 5px', fontSize: 9, cursor: 'pointer',
                                borderRadius: 5, border: state.gScale === p ? '1px solid #6366f1' : '1px solid #374151',
                                background: state.gScale === p ? '#312e81' : '#111827',
                                color: state.gScale === p ? '#a5b4fc' : '#9ca3af',
                            }}>×{p}</button>
                        )}
                    </div>
                    <input type="range" min={-3} max={1} step={0.001}
                        value={Math.log10(Math.max(state.gScale, 0.0001))}
                        onChange={e => setters.setGScale(parseFloat(Math.pow(10, +e.target.value).toPrecision(4)))}
                        style={{ width: '100%', marginTop: 4, accentColor: '#6366f1' }}
                    />
                </div>

                {/* Position + Rotation rows */}
                {ROWS.map(r => (
                    <div key={r.lbl} style={{ marginBottom: 7 }}>
                        <div style={label}>{r.lbl} <span style={{ color: '#f9fafb' }}>{r.display}</span></div>
                        <div style={row}>
                            {nudge('−−', step(r.set, r.cur, -r.delta * 2))}
                            {nudge('−', step(r.set, r.cur, -r.delta))}
                            {slider(r.cur, r.set, r.min, r.max, r.step)}
                            {nudge('+', step(r.set, r.cur, r.delta))}
                            {nudge('++', step(r.set, r.cur, r.delta * 2))}
                            <span style={val}>{r.display}</span>
                        </div>
                    </div>
                ))}
            </div>
        </Html>
    );
}

// ─── Placeholder (no modelUrl yet) ────────────────────────────────────────────

function PlaceholderAvatar() {
    const ref = useRef<THREE.Mesh>(null);
    useFrame((_, dt) => { if (ref.current) ref.current.rotation.y += dt * 0.1; });
    return (
        <Float speed={1.5} rotationIntensity={0.5} floatIntensity={1}>
            <mesh ref={ref} scale={1.2}>
                <capsuleGeometry args={[0.5, 1.5, 4, 16]} />
                <MeshDistortMaterial color="#4F46E5" attach="material"
                    distort={0.2} speed={2} roughness={0.2} metalness={0.8} wireframe />
            </mesh>
            <mesh position={[0, 1.2, 0]}>
                <sphereGeometry args={[0.4, 32, 32]} />
                <meshStandardMaterial color="#818cf8" roughness={0.3} metalness={0.8} />
            </mesh>
        </Float>
    );
}

// ─── Core loader ──────────────────────────────────────────────────────────────

function LoadedAvatar({
    url, garmentUrl,
    height = 170, weight = 70, bodyType = 'regular',
    animation = 'idle', showShirt = false,
}: {
    url: string; garmentUrl: string;
    height: number; weight: number; bodyType: string;
    animation?: string; showShirt?: boolean;
}) {
    // ── GLTF loads — explicit variable names to prevent aliasing ──────────
    const avatarGltf = useGLTF(url);
    const garmentGltf = useGLTF(garmentUrl);

    const { actions, names } = useAnimations(avatarGltf.animations, avatarGltf.scene);

    // ── Transform state ───────────────────────────────────────────────────
    const [gScale, setGScale] = useState(1);
    const [gPosX, setGPosX] = useState(0);
    const [gPosY, setGPosY] = useState(0);
    const [gPosZ, setGPosZ] = useState(0);
    const [gRotX, setGRotX] = useState(0);
    const [gRotY, setGRotY] = useState(0);
    const [gRotZ, setGRotZ] = useState(0);

    // ── Spine bone (memoised — only changes when the avatar scene changes) ──
    const spineAnchor = useMemo(() => findSpineAnchor(avatarGltf.scene), [avatarGltf.scene]);

    // ── Animation crossfade ───────────────────────────────────────────────
    useEffect(() => {
        if (!actions || Object.keys(actions).length === 0) return;
        Object.values(actions).forEach(a => a?.fadeOut(0.4));
        const target = actions[animation] ?? actions[names[0]];
        target?.reset().fadeIn(0.4).play();
    }, [animation, actions, names]);

    // ── Procedural animation fallback (Breathing) ─────────────────────────
    useFrame((state) => {
        const hasActions = actions && Object.keys(actions).length > 0;
        if (!hasActions && spineAnchor) {
            const t = state.clock.getElapsedTime();
            // Subtle breathing effect on the spine
            spineAnchor.rotation.x = Math.sin(t * 1.5) * 0.02;
            spineAnchor.scale.setScalar(1 + Math.sin(t * 1.5) * 0.005);
        }
    });

    // ── Morph targets ─────────────────────────────────────────────────────
    useEffect(() => {
        avatarGltf.scene.traverse(child => {
            const m = child as THREE.Mesh;
            if (!m.isMesh || !m.morphTargetDictionary || !m.morphTargetInfluences) return;
            const set = (k: string, v: number) => {
                const i = m.morphTargetDictionary![k];
                if (i !== undefined) m.morphTargetInfluences![i] = v;
            };
            set('Fat', Math.min(1, Math.max(0, (weight - 70) / 50)));
            set('Muscular', bodyType === 'athletic' ? 1 : 0);
            set('Tall', Math.min(1, Math.max(0, (height - 170) / 30)));
        });
    }, [avatarGltf.scene, height, weight, bodyType]);

    // ── Garment scene — clone once so we don't mutate the shared cache ────
    const garmentScene = useMemo(() => {
        if (garmentGltf.scene === avatarGltf.scene) {
            console.error('[AvatarViewer] garmentGltf.scene === avatarGltf.scene — URL collision?',
                '\n  avatar:', url, '\n  garment:', garmentUrl);
            return null;
        }
        return garmentGltf.scene.clone(true);
    }, [garmentGltf.scene, avatarGltf.scene, url, garmentUrl]);

    return (
        <>
            {/* Avatar body */}
            <primitive object={avatarGltf.scene} />

            {/* Garment — portaled into the spine bone */}
            {showShirt && garmentScene && (
                <>
                    {spineAnchor
                        ? createPortal(
                            <primitive
                                object={garmentScene}
                                position={[gPosX, gPosY, gPosZ]}
                                rotation={[gRotX, gRotY, gRotZ]}
                                scale={gScale}
                            />,
                            spineAnchor
                        )
                        : /* no bone found — render in world space as fallback */
                        <primitive
                            object={garmentScene}
                            position={[gPosX, gPosY, gPosZ]}
                            rotation={[gRotX, gRotY, gRotZ]}
                            scale={gScale}
                        />
                    }

                    {/* Diagnostic: red sphere when no bone was found */}
                    {!spineAnchor && (
                        <mesh position={[0, 1, 0]}>
                            <sphereGeometry args={[0.08, 12, 12]} />
                            <meshBasicMaterial color="#ff0000" wireframe />
                        </mesh>
                    )}

                    <DebugPanel
                        state={{ gScale, gPosX, gPosY, gPosZ, gRotX, gRotY, gRotZ }}
                        setters={{ setGScale, setGPosX, setGPosY, setGPosZ, setGRotX, setGRotY, setGRotZ }}
                        boneName={spineAnchor?.name ?? ''}
                    />
                </>
            )}
        </>
    );
}

// ─── Error fallback ───────────────────────────────────────────────────────────

function AvatarErrorFallback({ error }: FallbackProps) {
    console.error('[AvatarViewer] GLB error:', error);
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
    height, weight, bodyType, animation,
    showShirt,
    garmentUrl = '/models/garments/t-shirt.glb',
}: AvatarViewerProps) {
    return (
        // key forces full teardown + remount whenever the model URL changes,
        // so useGLTF always loads the correct new model from scratch.
        <group key={modelUrl ?? '__placeholder__'} position={[0, -0.5, 0]}>
            {modelUrl ? (
                <ErrorBoundary key={modelUrl} FallbackComponent={AvatarErrorFallback}>
                    <Suspense fallback={<PlaceholderAvatar />}>
                        <LoadedAvatar
                            url={modelUrl}
                            garmentUrl={garmentUrl}
                            height={height ?? 170}
                            weight={weight ?? 70}
                            bodyType={bodyType ?? 'regular'}
                            animation={animation}
                            showShirt={showShirt}
                        />
                    </Suspense>
                </ErrorBoundary>
            ) : (
                <PlaceholderAvatar />
            )}
        </group>
    );
}

// Pre-warm GLTF cache for Studio's most common models
useGLTF.preload('/models/Male.glb');
useGLTF.preload('/models/Female.glb');
useGLTF.preload('/models/garments/t-shirt.glb');
