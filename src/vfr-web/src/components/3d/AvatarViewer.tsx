import { useRef, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import { Float, MeshDistortMaterial, useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import { ErrorBoundary } from 'react-error-boundary';

interface AvatarViewerProps {
    modelUrl?: string | null;
    height?: number;
    weight?: number;
    bodyType?: string;
}

// A simple fallback if no 3D model URL is provided yet
function PlaceholderAvatar() {
    const meshRef = useRef<THREE.Mesh>(null);

    useFrame((_, delta) => {
        if (meshRef.current) {
            meshRef.current.rotation.y += delta * 0.1;
        }
    });

    return (
        <Float speed={1.5} rotationIntensity={0.5} floatIntensity={1}>
            <mesh ref={meshRef} position={[0, 0, 0]} scale={1.2}>
                <capsuleGeometry args={[0.5, 1.5, 4, 16]} />
                <MeshDistortMaterial
                    color="#4F46E5"
                    attach="material"
                    distort={0.2}
                    speed={2}
                    roughness={0.2}
                    metalness={0.8}
                    wireframe
                />
            </mesh>
            {/* A simulated head */}
            <mesh position={[0, 1.2, 0]}>
                <sphereGeometry args={[0.4, 32, 32]} />
                <meshStandardMaterial color="#818cf8" roughness={0.3} metalness={0.8} />
            </mesh>
        </Float>
    );
}

// Loads a realistic Avatar GLB if provided
function LoadedAvatar({ url, height = 170, weight = 70, bodyType = 'regular' }: { url: string, height: number, weight: number, bodyType: string }) {
    // React Suspense relies on throwing Promises
    const { scene } = useGLTF(url);

    useEffect(() => {
        if (!scene) return;

        // 1. Calculate base scalars (170cm, 70kg as baseline 1.0)
        const hScale = height / 170;
        const wScale = weight / 70;

        // Reset all specific bone scales to prevent compounding frame-over-frame
        scene.traverse((child) => {
            if (child.name.includes('mixamorig')) {
                child.scale.set(1, 1, 1);
            }
        });

        // 2. Local Morph Heuristics
        let pelvisScale = 1;
        let chestScale = 1;
        let waistScale = 1;

        if (bodyType === 'athletic') {
            waistScale = 0.9;
            pelvisScale = 0.95;
            chestScale = 1.25; // Broad shoulders
        } else if (bodyType === 'curvy') {
            waistScale = 0.85;
            pelvisScale = 1.25; // Wide hips
            chestScale = 1.1;
        } else if (bodyType === 'slim') {
            pelvisScale = 0.9;
            chestScale = 0.9;
        }

        // Apply local bone scaling for realistic human morphs
        scene.traverse((child) => {
            if (child.name === 'mixamorigHips') {
                child.scale.set(pelvisScale, 1, pelvisScale);
            }
            if (child.name === 'mixamorigSpine') {
                child.scale.set(waistScale, 1, waistScale);
            }
            if (child.name === 'mixamorigSpine2') {
                child.scale.set(chestScale, 1, chestScale);
            }
        });

        // 3. Apply global height & weight scalars to the exact root mesh
        scene.scale.set(wScale, hScale, wScale);

    }, [scene, height, weight, bodyType]);

    return <primitive object={scene} />;
}

function AvatarErrorFallback({ error }: any) {
    console.error("ErrorBoundary caught GLTF parse error:", error);
    return (
        <mesh position={[0, 0, 0]} scale={1.2}>
            <capsuleGeometry args={[0.5, 1.5, 4, 32]} />
            <meshStandardMaterial color="#ef4444" roughness={0.4} metalness={0.1} />
        </mesh>
    );
}

export default function AvatarViewer({ modelUrl, height, weight, bodyType }: AvatarViewerProps) {
    return (
        <group position={[0, -0.5, 0]}>
            {modelUrl ? (
                <ErrorBoundary FallbackComponent={AvatarErrorFallback}>
                    <LoadedAvatar url={modelUrl} height={height || 170} weight={weight || 70} bodyType={bodyType || 'regular'} />
                </ErrorBoundary>
            ) : (
                <PlaceholderAvatar />
            )}
        </group>
    );
}
