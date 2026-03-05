import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Float, MeshDistortMaterial, useGLTF } from '@react-three/drei';
import * as THREE from 'three';

interface AvatarViewerProps {
    modelUrl?: string | null;
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
function LoadedAvatar({ url }: { url: string }) {
    // We now load the generated SMPL model here via useGLTF
    // React Suspense relies on throwing Promises, so try/catch breaks it here.
    const { scene } = useGLTF(url);
    return <primitive object={scene} />;
}

export default function AvatarViewer({ modelUrl }: AvatarViewerProps) {
    return (
        <group position={[0, -0.5, 0]}>
            {modelUrl ? <LoadedAvatar url={modelUrl} /> : <PlaceholderAvatar />}
        </group>
    );
}
