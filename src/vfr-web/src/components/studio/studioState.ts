export type StudioGender = 'male' | 'female';
export type ViewportMode = 'preview' | 'generated';

export type AutoMeasurementsState = {
    chest: number;
    waist: number;
    hip: number;
    armLength: number;
    legLength: number;
};

export type ManualMeasurementsState = {
    chest: number;
    waist: number;
    hip: number;
    shoulder: number;
    calf: number;
    armLength: number;
    torsoLength: number;
    legLength: number;
};

export type StudioDraftSnapshot = {
    height: number;
    weight: number;
    bodyType: string;
    gender: StudioGender;
    muscularity: number;
    bodyFatPercentage: number;
    manualMeasurements: ManualMeasurementsState;
    autoMeasurements: AutoMeasurementsState;
};

export type StudioGeneratedAvatarState = {
    modelUrl: string | null;
    generatedAt: string | null;
    inputHash: string | null;
    isCurrent: boolean;
};

export type StudioProfileResponse = {
    id?: string;
    userId?: string;
    height?: number;
    weight?: number;
    bodyType?: string;
    gender?: string;
    muscularity?: number | null;
    bodyFatPercentage?: number | null;
    draftStateHash?: string | null;
    lastAvatarModelUrl?: string | null;
    generatedAvatar?: {
        modelUrl?: string | null;
        generatedAt?: string | null;
        inputHash?: string | null;
        isCurrent?: boolean | null;
    };
    manualMeasurements?: {
        chestCircumference?: number | null;
        waistCircumference?: number | null;
        hipCircumference?: number | null;
        shoulderWidth?: number | null;
        calfCircumference?: number | null;
        armLength?: number | null;
        torsoLength?: number | null;
        legLength?: number | null;
    };
    autoMeasurements?: {
        chestCircumference?: number | null;
        waistCircumference?: number | null;
        hipCircumference?: number | null;
        armLength?: number | null;
        legLength?: number | null;
    };
};

export const EMPTY_AUTO_MEASUREMENTS: AutoMeasurementsState = {
    chest: 0,
    waist: 0,
    hip: 0,
    armLength: 0,
    legLength: 0,
};

export const EMPTY_MANUAL_MEASUREMENTS: ManualMeasurementsState = {
    chest: 0,
    waist: 0,
    hip: 0,
    shoulder: 0,
    calf: 0,
    armLength: 0,
    torsoLength: 0,
    legLength: 0,
};

const toNullableMeasurement = (value: number) => (value > 0 ? value : null);

const normalizeNumber = (value: number) => Number.parseFloat(value.toFixed(2)).toString();
const normalizeNullableNumber = (value: number | null | undefined) => value == null ? '-' : normalizeNumber(value);

export const mapManualMeasurements = (
    measurements?: StudioProfileResponse['manualMeasurements'] | Record<string, unknown> | null,
): ManualMeasurementsState => {
    const source = (measurements ?? {}) as Record<string, unknown>;
    return {
        chest: Number(source.chestCircumference ?? 0),
        waist: Number(source.waistCircumference ?? 0),
        hip: Number(source.hipCircumference ?? 0),
        shoulder: Number(source.shoulderWidth ?? 0),
        calf: Number(source.calfCircumference ?? 0),
        armLength: Number(source.armLength ?? 0),
        torsoLength: Number(source.torsoLength ?? 0),
        legLength: Number(source.legLength ?? 0),
    };
};

export const mapAutoMeasurements = (
    measurements?: StudioProfileResponse['autoMeasurements'] | Record<string, unknown> | null,
): AutoMeasurementsState => {
    const source = (measurements ?? {}) as Record<string, unknown>;
    return {
        chest: Number(source.chestCircumference ?? source.chest_cm ?? 0),
        waist: Number(source.waistCircumference ?? source.waist_cm ?? 0),
        hip: Number(source.hipCircumference ?? source.hips_cm ?? 0),
        armLength: Number(source.armLength ?? source.arm_length_cm ?? 0),
        legLength: Number(source.legLength ?? source.leg_length_cm ?? 0),
    };
};

export const buildStudioDraftFingerprintSource = (draft: StudioDraftSnapshot) => [
    normalizeNumber(draft.height),
    normalizeNumber(draft.weight),
    draft.bodyType.toLowerCase(),
    draft.gender.toLowerCase(),
    normalizeNumber(draft.muscularity),
    normalizeNumber(draft.bodyFatPercentage),
    normalizeNullableNumber(toNullableMeasurement(draft.manualMeasurements.chest)),
    normalizeNullableNumber(toNullableMeasurement(draft.manualMeasurements.waist)),
    normalizeNullableNumber(toNullableMeasurement(draft.manualMeasurements.hip)),
    normalizeNullableNumber(toNullableMeasurement(draft.manualMeasurements.shoulder)),
    normalizeNullableNumber(toNullableMeasurement(draft.manualMeasurements.calf)),
    normalizeNullableNumber(toNullableMeasurement(draft.manualMeasurements.armLength)),
    normalizeNullableNumber(toNullableMeasurement(draft.manualMeasurements.torsoLength)),
    normalizeNullableNumber(toNullableMeasurement(draft.manualMeasurements.legLength)),
].join('|');

export async function createStudioDraftFingerprint(draft: StudioDraftSnapshot): Promise<string> {
    const source = buildStudioDraftFingerprintSource(draft);
    const encoded = new TextEncoder().encode(source);
    const digest = await crypto.subtle.digest('SHA-256', encoded);
    return Array.from(new Uint8Array(digest))
        .map(byte => byte.toString(16).padStart(2, '0'))
        .join('');
}
