import React, { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Environment, ContactShadows } from '@react-three/drei';
import AvatarViewer from '../3d/AvatarViewer';
import CameraController from '../3d/CameraController';

interface Scene3DProps {
    avatarUrl: string | null;
    gender: 'male' | 'female';
    height: number;
    weight: number;
    bodyType: string;
    animation: string;
    showShirt: boolean;
    cameraResetTick: number;
    cameraView: 'front' | 'back' | 'left' | 'right' | 'face';
    localHeight: number;
}

const Scene3D: React.FC<Scene3DProps> = ({
    avatarUrl,
    gender,
    height,
    weight,
    bodyType,
    animation,
    showShirt,
    cameraResetTick,
    cameraView,
    localHeight
}) => {
    return (
        <Canvas
            camera={{ position: [0, 1.2, 4], fov: 45 }}
            gl={{ antialias: true, alpha: true, preserveDrawingBuffer: true }}
            dpr={[1, 2]}
        >
            <Suspense fallback={null}>
                <Environment preset="city" />
                <ambientLight intensity={0.4} />
                <spotLight position={[5, 5, 5]} angle={0.2} penumbra={1} intensity={1} castShadow />
                <directionalLight position={[-5, 5, -5]} intensity={0.5} />

                <AvatarViewer
                    key={avatarUrl ?? gender}
                    modelUrl={avatarUrl ?? (gender === 'male' ? '/models/Male.glb' : '/models/Female.glb')}
                    height={height}
                    weight={weight}
                    bodyType={bodyType}
                    gender={gender}
                    animation={animation as any}
                    showShirt={showShirt}
                />

                <CameraController avatarHeight={localHeight / 100} trigger={cameraResetTick} view={cameraView} />
                
                <ContactShadows position={[0, -1, 0]} opacity={0.4} scale={10} blur={2} far={4} />
                <OrbitControls
                    makeDefault
                    enablePan={false}
                    enableZoom={true}
                    minDistance={2}
                    maxDistance={6}
                    maxPolarAngle={Math.PI / 2 + 0.1}
                    target={[0, 1, 0]}
                    autoRotate
                    autoRotateSpeed={0.5}
                />
            </Suspense>
        </Canvas>
    );
};

export default Scene3D;
