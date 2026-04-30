import { useEffect, useRef } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { createLogger } from '../../lib/logger';

const logger = createLogger('VFR.Web.CameraController');

interface CameraControllerProps {
    avatarHeight: number; // Height in meters
    trigger: number;      // Increment to trigger reframing
    view: 'front' | 'back' | 'left' | 'right' | 'face';
}

type OrbitControlsLike = {
    target: THREE.Vector3;
    update: () => void;
};

export default function CameraController({ avatarHeight, trigger, view }: CameraControllerProps) {
    const { camera } = useThree();
    
    // We keep track of where we want the camera and the target to be
    const targetPosition = useRef(new THREE.Vector3(0, 1.2, 4));
    const targetLookAt = useRef(new THREE.Vector3(0, 1, 0));
    const isAnimating = useRef(false);

    useEffect(() => {
        const centerY = avatarHeight / 2;
        const lookAtY = centerY;

        // Calculate distance to fit the avatar using trigonometry
        let fov = 45; // default FOV
        if ((camera as THREE.PerspectiveCamera).isPerspectiveCamera) {
            fov = (camera as THREE.PerspectiveCamera).fov;
        }
        
        // Convert FOV to radians and divide by box height
        const fovRad = (fov * Math.PI) / 360;
        
        // Add 1.2 padding factor so the head/feet aren't touching the edge
        const padding = 1.2;
        const requiredDistance = ((avatarHeight * padding) / 2) / Math.tan(fovRad);
        
        switch (view) {
            case 'front':
                targetPosition.current.set(0, centerY, requiredDistance);
                targetLookAt.current.set(0, lookAtY, 0);
                break;
            case 'back':
                targetPosition.current.set(0, centerY, -requiredDistance);
                targetLookAt.current.set(0, lookAtY, 0);
                break;
            case 'left':
                targetPosition.current.set(requiredDistance, centerY, 0);
                targetLookAt.current.set(0, lookAtY, 0);
                break;
            case 'right':
                targetPosition.current.set(-requiredDistance, centerY, 0);
                targetLookAt.current.set(0, lookAtY, 0);
                break;
            case 'face':
                targetPosition.current.set(0, avatarHeight * 0.9, requiredDistance * 0.3);
                targetLookAt.current.set(0, avatarHeight * 0.9, 0);
                break;
        }

        isAnimating.current = true;
    }, [avatarHeight, trigger, view, camera]);

    useFrame((state, delta) => {
        if (!isAnimating.current) return;

        // 1. Smoothly move camera and target using delta for frame-independent speed
        const speed = 5.0;
        state.camera.position.lerp(targetPosition.current, delta * speed);
        
        const controls = (state as typeof state & { controls?: OrbitControlsLike }).controls;
        if (controls) {
            controls.target.lerp(targetLookAt.current, delta * speed);
            controls.update();
        }

        // 2. The Release Mechanism (Check distance)
        const dist = state.camera.position.distanceTo(targetPosition.current);
        
        if (dist < 0.1) { // 10cm threshold is safe
            // Snap exactly to target to prevent micro-jitters
            state.camera.position.copy(targetPosition.current);
            if (controls) {
                controls.target.copy(targetLookAt.current);
                controls.update();
            }
            
            // RELEASE CONTROL
            isAnimating.current = false;
            logger.debug('Camera animation completed.', { view });
        }
    });

    return null;
}
