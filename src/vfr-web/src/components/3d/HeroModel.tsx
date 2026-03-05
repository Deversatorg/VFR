import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Float, MeshDistortMaterial, Environment, Sparkles } from '@react-three/drei';
import * as THREE from 'three';

export default function HeroModel() {
    const meshRef = useRef<THREE.Mesh>(null);

    useFrame((_, delta) => {
        if (meshRef.current) {
            meshRef.current.rotation.x += delta * 0.2;
            meshRef.current.rotation.y += delta * 0.3;
        }
    });

    return (
        <>
            {/* Ambient & Directional Lighting for contrast */}
            <ambientLight intensity={0.2} />
            <directionalLight position={[10, 10, 5]} intensity={2} color="#4285F4" />
            <directionalLight position={[-10, -10, -5]} intensity={1} color="#135bec" />

            {/* Floating, distorting abstract geometry to look "neural" and premium */}
            <Float speed={2} rotationIntensity={1.5} floatIntensity={2}>
                <mesh ref={meshRef} scale={1.8}>
                    <icosahedronGeometry args={[1, 12]} />
                    <MeshDistortMaterial
                        color="#135bec"
                        attach="material"
                        distort={0.4}
                        speed={1.5}
                        roughness={0.1}
                        metalness={0.8}
                        clearcoat={1}
                        clearcoatRoughness={0.1}
                        envMapIntensity={2}
                    />
                </mesh>
            </Float>

            {/* Elegant particles surrounding */}
            <Sparkles count={200} scale={12} size={4} speed={0.4} opacity={0.2} color="#ffffff" />

            {/* Environment reflection map for the shiny distorted look */}
            <Environment preset="city" />
        </>
    );
}
