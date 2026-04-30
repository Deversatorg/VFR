import { Suspense, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import { createPortal, useFrame } from '@react-three/fiber';
import { ErrorBoundary, type FallbackProps } from 'react-error-boundary';
import { Float, Html, MeshDistortMaterial, useAnimations, useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import { createLogger } from '../../lib/logger';

export interface AvatarViewerProps {
    modelUrl?: string | null;
    renderMode?: 'preview' | 'generated';
    height?: number;
    weight?: number;
    bodyType?: string;
    muscularity?: number;
    bodyFatPercentage?: number;
    gender?: 'male' | 'female';
    animation?: 'idle' | 'walk' | 'run' | 'jump' | 'tpose';
    showGarment?: boolean;
    garmentUrl?: string;
    garmentTint?: string;
    showGarmentDebug?: boolean;
}

const DEFAULT_GARMENT_URL = '/models/garments/t-shirt.glb';
const logger = createLogger('VFR.Web.AvatarViewer');

const SPINE_CANDIDATES = [
    'mixamorig:Spine2',
    'mixamorig:Spine1',
    'mixamorig:Spine',
    'Spine2',
    'Spine1',
    'Spine',
    'Chest',
    'chest',
    'spine_3',
    'spine_2',
    'spine_1',
    'spine',
    'pelvis',
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
        if (bone) {
            return bone;
        }
        const node = nodeMap.get(name);
        if (node) {
            return node;
        }
    }

    let fallback: THREE.Object3D | null = null;
    root.traverse(node => {
        if (!fallback && node.name) {
            const normalized = node.name.toLowerCase();
            if (normalized.includes('spine') || normalized.includes('chest') || normalized.includes('pelvis')) {
                fallback = node;
            }
        }
    });

    return fallback;
}

function cloneMaterialWithTint(material: THREE.Material, tint?: string) {
    const clonedMaterial = material.clone();
    if (tint) {
        const maybeColorMaterial = clonedMaterial as THREE.Material & { color?: THREE.Color };
        if (maybeColorMaterial.color instanceof THREE.Color) {
            maybeColorMaterial.color.set(tint);
        }
    }
    return clonedMaterial;
}

function cloneGarmentScene(scene: THREE.Object3D, tint?: string) {
    const clonedScene = scene.clone(true);
    clonedScene.traverse(node => {
        const mesh = node as THREE.Mesh;
        if (!mesh.isMesh) {
            return;
        }

        mesh.castShadow = true;
        mesh.receiveShadow = true;

        if (Array.isArray(mesh.material)) {
            mesh.material = mesh.material.map(material => cloneMaterialWithTint(material, tint));
            return;
        }

        if (mesh.material) {
            mesh.material = cloneMaterialWithTint(mesh.material, tint);
        }
    });

    return clonedScene;
}

interface TransformState {
    gScale: number;
    gPosX: number;
    gPosY: number;
    gPosZ: number;
    gRotX: number;
    gRotY: number;
    gRotZ: number;
}

interface TransformSetters {
    setGScale: (value: number) => void;
    setGPosX: (value: number) => void;
    setGPosY: (value: number) => void;
    setGPosZ: (value: number) => void;
    setGRotX: (value: number) => void;
    setGRotY: (value: number) => void;
    setGRotZ: (value: number) => void;
}

function DebugPanel({
    state,
    setters,
    boneName,
}: {
    state: TransformState;
    setters: TransformSetters;
    boneName: string;
}) {
    const formatValue = (value: number) => value.toFixed(3);
    const formatDegrees = (value: number) => `${((value * 180) / Math.PI).toFixed(1)} deg`;
    const step = (setValue: (value: number) => void, currentValue: number, delta: number) =>
        () => setValue(parseFloat((currentValue + delta).toFixed(4)));

    const resetAll = () => {
        setters.setGScale(1);
        setters.setGPosX(0);
        setters.setGPosY(0);
        setters.setGPosZ(0);
        setters.setGRotX(0);
        setters.setGRotY(0);
        setters.setGRotZ(0);
    };

    const panelStyle: CSSProperties = {
        position: 'fixed',
        top: 12,
        right: 12,
        width: 280,
        padding: '14px 16px',
        borderRadius: 16,
        border: '1px solid rgba(255,255,255,0.09)',
        background: 'rgba(8,8,12,0.93)',
        backdropFilter: 'blur(14px)',
        boxShadow: '0 8px 40px rgba(0,0,0,0.7)',
        fontFamily: 'monospace',
        fontSize: 11,
        color: '#e5e7eb',
        pointerEvents: 'auto',
        userSelect: 'none',
    };

    const labelStyle: CSSProperties = {
        marginBottom: 3,
        color: '#6b7280',
        fontSize: 9,
        letterSpacing: 1.2,
        textTransform: 'uppercase',
    };

    const rowStyle: CSSProperties = {
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        marginBottom: 8,
    };

    const valueStyle: CSSProperties = {
        minWidth: 52,
        textAlign: 'right',
        color: '#f9fafb',
        fontSize: 11,
    };

    const renderNudge = (label: string, onClick: () => void) => (
        <button
            key={label}
            onClick={onClick}
            style={{
                padding: '2px 6px',
                fontSize: 10,
                cursor: 'pointer',
                borderRadius: 5,
                border: '1px solid #374151',
                background: '#111827',
                color: '#9ca3af',
            }}
        >
            {label}
        </button>
    );

    const renderSlider = (
        value: number,
        setValue: (nextValue: number) => void,
        min: number,
        max: number,
        stepValue: number,
    ) => (
        <input
            type="range"
            min={min}
            max={max}
            step={stepValue}
            value={value}
            onChange={event => setValue(Number(event.target.value))}
            style={{ flex: 1, accentColor: '#6366f1', cursor: 'pointer' }}
        />
    );

    const rows = [
        { label: 'Pos X', display: formatValue(state.gPosX), current: state.gPosX, set: setters.setGPosX, min: -2, max: 2, step: 0.001, delta: 0.01 },
        { label: 'Pos Y', display: formatValue(state.gPosY), current: state.gPosY, set: setters.setGPosY, min: -2, max: 2, step: 0.001, delta: 0.01 },
        { label: 'Pos Z', display: formatValue(state.gPosZ), current: state.gPosZ, set: setters.setGPosZ, min: -2, max: 2, step: 0.001, delta: 0.01 },
        { label: 'Rot X', display: formatDegrees(state.gRotX), current: state.gRotX, set: setters.setGRotX, min: -Math.PI, max: Math.PI, step: 0.01, delta: Math.PI / 16 },
        { label: 'Rot Y', display: formatDegrees(state.gRotY), current: state.gRotY, set: setters.setGRotY, min: -Math.PI, max: Math.PI, step: 0.01, delta: Math.PI / 16 },
        { label: 'Rot Z', display: formatDegrees(state.gRotZ), current: state.gRotZ, set: setters.setGRotZ, min: -Math.PI, max: Math.PI, step: 0.01, delta: Math.PI / 16 },
    ];

    return (
        <Html prepend zIndexRange={[200, 0]} style={{ pointerEvents: 'none' }}>
            <div style={panelStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                    <span style={{ color: '#818cf8', fontWeight: 700, fontSize: 12, letterSpacing: 1 }}>
                        GARMENT DEBUG
                    </span>
                    <button
                        onClick={resetAll}
                        style={{
                            padding: '2px 8px',
                            fontSize: 9,
                            cursor: 'pointer',
                            borderRadius: 5,
                            border: '1px solid #374151',
                            background: '#1f2937',
                            color: '#9ca3af',
                        }}
                    >
                        RESET ALL
                    </button>
                </div>

                <div style={{ marginBottom: 10, color: '#6b7280', fontSize: 9 }}>
                    BONE:{' '}
                    <span style={{ color: boneName ? '#34d399' : '#f87171' }}>
                        {boneName || 'not found'}
                    </span>
                </div>

                <div style={{ marginBottom: 10 }}>
                    <div style={labelStyle}>
                        Scale <span style={{ color: '#f9fafb' }}>{state.gScale}</span>
                    </div>
                    <div style={rowStyle}>
                        {[0.001, 0.01, 0.1, 1, 10].map(preset => (
                            <button
                                key={preset}
                                onClick={() => setters.setGScale(preset)}
                                style={{
                                    padding: '2px 5px',
                                    fontSize: 9,
                                    cursor: 'pointer',
                                    border: state.gScale === preset ? '1px solid #6366f1' : '1px solid #374151',
                                    borderRadius: 5,
                                    background: state.gScale === preset ? '#312e81' : '#111827',
                                    color: state.gScale === preset ? '#a5b4fc' : '#9ca3af',
                                }}
                            >
                                x{preset}
                            </button>
                        ))}
                    </div>
                    <input
                        type="range"
                        min={-3}
                        max={1}
                        step={0.001}
                        value={Math.log10(Math.max(state.gScale, 0.0001))}
                        onChange={event =>
                            setters.setGScale(
                                parseFloat(Math.pow(10, Number(event.target.value)).toPrecision(4)),
                            )
                        }
                        style={{ width: '100%', marginTop: 4, accentColor: '#6366f1' }}
                    />
                </div>

                {rows.map(row => (
                    <div key={row.label} style={{ marginBottom: 7 }}>
                        <div style={labelStyle}>
                            {row.label} <span style={{ color: '#f9fafb' }}>{row.display}</span>
                        </div>
                        <div style={rowStyle}>
                            {renderNudge('--', step(row.set, row.current, -row.delta * 2))}
                            {renderNudge('-', step(row.set, row.current, -row.delta))}
                            {renderSlider(row.current, row.set, row.min, row.max, row.step)}
                            {renderNudge('+', step(row.set, row.current, row.delta))}
                            {renderNudge('++', step(row.set, row.current, row.delta * 2))}
                            <span style={valueStyle}>{row.display}</span>
                        </div>
                    </div>
                ))}
            </div>
        </Html>
    );
}

function PlaceholderAvatar() {
    const ref = useRef<THREE.Mesh>(null);

    useFrame((_, delta) => {
        if (ref.current) {
            ref.current.rotation.y += delta * 0.1;
        }
    });

    return (
        <Float speed={1.5} rotationIntensity={0.5} floatIntensity={1}>
            <mesh ref={ref} scale={1.2}>
                <capsuleGeometry args={[0.5, 1.5, 4, 16]} />
                <MeshDistortMaterial
                    attach="material"
                    color="#4F46E5"
                    distort={0.2}
                    speed={2}
                    roughness={0.2}
                    metalness={0.8}
                    wireframe
                />
            </mesh>
            <mesh position={[0, 1.2, 0]}>
                <sphereGeometry args={[0.4, 32, 32]} />
                <meshStandardMaterial color="#818cf8" roughness={0.3} metalness={0.8} />
            </mesh>
        </Float>
    );
}

function LoadedAvatar({
    url,
    garmentUrl,
    garmentTint,
    height = 170,
    weight = 70,
    bodyType = 'regular',
    muscularity = 50,
    bodyFatPercentage = 20,
    animation = 'idle',
    showGarment = false,
    showGarmentDebug = false,
    applyLiveShape = false,
}: {
    url: string;
    garmentUrl: string;
    garmentTint?: string;
    height: number;
    weight: number;
    bodyType: string;
    muscularity: number;
    bodyFatPercentage: number;
    animation?: string;
    showGarment?: boolean;
    showGarmentDebug?: boolean;
    applyLiveShape?: boolean;
}) {
    const avatarGltf = useGLTF(url);
    const garmentGltf = useGLTF(garmentUrl);
    const { actions, names } = useAnimations(avatarGltf.animations, avatarGltf.scene);

    const [gScale, setGScale] = useState(1);
    const [gPosX, setGPosX] = useState(0);
    const [gPosY, setGPosY] = useState(0);
    const [gPosZ, setGPosZ] = useState(0);
    const [gRotX, setGRotX] = useState(0);
    const [gRotY, setGRotY] = useState(0);
    const [gRotZ, setGRotZ] = useState(0);

    const spineAnchor = useMemo(() => findSpineAnchor(avatarGltf.scene), [avatarGltf.scene]);
    const spineAnchorRef = useRef<THREE.Object3D | null>(spineAnchor);

    useEffect(() => {
        spineAnchorRef.current = spineAnchor;
    }, [spineAnchor]);

    useEffect(() => {
        if (!actions || Object.keys(actions).length === 0) {
            return;
        }

        Object.values(actions).forEach(action => action?.fadeOut(0.4));
        const targetAction = actions[animation] ?? actions[names[0]];
        targetAction?.reset().fadeIn(0.4).play();
    }, [animation, actions, names]);

    useFrame(state => {
        const hasActions = actions && Object.keys(actions).length > 0;
        const animatedSpineAnchor = spineAnchorRef.current;
        if (!hasActions && animatedSpineAnchor) {
            const time = state.clock.getElapsedTime();
            animatedSpineAnchor.rotation.x = Math.sin(time * 1.5) * 0.02;
            animatedSpineAnchor.scale.setScalar(1 + Math.sin(time * 1.5) * 0.005);
        }
    });

    useEffect(() => {
        if (!applyLiveShape) {
            return;
        }

        const clamp01 = (value: number) => Math.min(1, Math.max(0, value));

        avatarGltf.scene.traverse(child => {
            const mesh = child as THREE.Mesh;
            if (!mesh.isMesh || !mesh.morphTargetDictionary || !mesh.morphTargetInfluences) {
                return;
            }

            const setMorph = (key: string, value: number) => {
                const morphIndex = mesh.morphTargetDictionary![key];
                if (morphIndex !== undefined) {
                    mesh.morphTargetInfluences![morphIndex] = value;
                }
            };

            const fatFromWeight = clamp01((weight - 70) / 50);
            const fatFromComposition = clamp01((bodyFatPercentage - 10) / 30);
            const muscularFromBodyType =
                bodyType === 'athletic' ? 0.65 :
                bodyType === 'slim' ? 0.25 :
                bodyType === 'curvy' ? 0.35 :
                0.45;
            const muscularFromComposition = clamp01(muscularity / 100);
            const tallFromHeight = clamp01((height - 170) / 30);

            const fatMorph = clamp01(fatFromWeight * 0.35 + fatFromComposition * 0.65);
            const muscularMorph = clamp01(muscularFromBodyType * 0.25 + muscularFromComposition * 0.75);

            setMorph('Fat', fatMorph);
            setMorph('Muscular', muscularMorph);
            setMorph('Tall', tallFromHeight);
        });
    }, [applyLiveShape, avatarGltf.scene, height, weight, bodyType, muscularity, bodyFatPercentage]);

    const garmentScene = useMemo(() => {
        if (garmentGltf.scene === avatarGltf.scene) {
            logger.error('Garment scene collided with avatar scene.', {
                avatar_url: url,
                garment_url: garmentUrl,
            });
            return null;
        }

        return cloneGarmentScene(garmentGltf.scene, garmentTint);
    }, [garmentGltf.scene, avatarGltf.scene, garmentTint, url, garmentUrl]);

    return (
        <>
            <primitive object={avatarGltf.scene} />

            {showGarment && garmentScene && (
                <>
                    {spineAnchor ? (
                        createPortal(
                            <primitive
                                object={garmentScene}
                                position={[gPosX, gPosY, gPosZ]}
                                rotation={[gRotX, gRotY, gRotZ]}
                                scale={gScale}
                            />,
                            spineAnchor,
                        )
                    ) : (
                        <primitive
                            object={garmentScene}
                            position={[gPosX, gPosY, gPosZ]}
                            rotation={[gRotX, gRotY, gRotZ]}
                            scale={gScale}
                        />
                    )}

                    {!spineAnchor && (
                        <mesh position={[0, 1, 0]}>
                            <sphereGeometry args={[0.08, 12, 12]} />
                            <meshBasicMaterial color="#ff0000" wireframe />
                        </mesh>
                    )}

                    {showGarmentDebug && (
                        <DebugPanel
                            state={{ gScale, gPosX, gPosY, gPosZ, gRotX, gRotY, gRotZ }}
                            setters={{ setGScale, setGPosX, setGPosY, setGPosZ, setGRotX, setGRotY, setGRotZ }}
                            boneName={spineAnchor?.name ?? ''}
                        />
                    )}
                </>
            )}
        </>
    );
}

function AvatarErrorFallback({ error }: FallbackProps) {
    logger.error('Avatar GLB render failed.', undefined, error);

    return (
        <mesh scale={1.2}>
            <capsuleGeometry args={[0.5, 1.5, 4, 32]} />
            <meshStandardMaterial color="#ef4444" roughness={0.4} metalness={0.1} />
        </mesh>
    );
}

export default function AvatarViewer({
    modelUrl,
    renderMode = 'preview',
    height,
    weight,
    bodyType,
    muscularity,
    bodyFatPercentage,
    animation,
    showGarment = false,
    garmentUrl = DEFAULT_GARMENT_URL,
    garmentTint,
    showGarmentDebug = false,
}: AvatarViewerProps) {
    return (
        <group key={`${renderMode}:${modelUrl ?? '__placeholder__'}`} position={[0, -0.5, 0]}>
            {modelUrl ? (
                <ErrorBoundary key={`${renderMode}:${modelUrl}`} FallbackComponent={AvatarErrorFallback}>
                    <Suspense fallback={<PlaceholderAvatar />}>
                        <LoadedAvatar
                            url={modelUrl}
                            garmentUrl={garmentUrl}
                            garmentTint={garmentTint}
                            height={height ?? 170}
                            weight={weight ?? 70}
                            bodyType={bodyType ?? 'regular'}
                            muscularity={muscularity ?? 50}
                            bodyFatPercentage={bodyFatPercentage ?? 20}
                            animation={animation}
                            showGarment={showGarment}
                            showGarmentDebug={showGarmentDebug}
                            applyLiveShape={renderMode === 'preview'}
                        />
                    </Suspense>
                </ErrorBoundary>
            ) : (
                <PlaceholderAvatar />
            )}
        </group>
    );
}

useGLTF.preload('/models/Male.glb');
useGLTF.preload('/models/Female.glb');
useGLTF.preload(DEFAULT_GARMENT_URL);
