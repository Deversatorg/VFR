type LogLevel = 'debug' | 'info' | 'warn' | 'error';
type LogFields = Record<string, unknown>;

const APP_ENVIRONMENT = import.meta.env.VITE_APP_ENVIRONMENT || import.meta.env.MODE || 'development';
const SERVICE_NAME = 'vfr-web';
const SERVICE_NAMESPACE = 'virtual-fitting-room';
const CLIENT_SESSION_STORAGE_KEY = 'vfr.client_session_id';

let cachedSessionId: string | null = null;

function generateId() {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
        return crypto.randomUUID();
    }

    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function getStorage() {
    try {
        if (typeof window !== 'undefined' && window.sessionStorage) {
            return window.sessionStorage;
        }
    } catch {
        return null;
    }

    return null;
}

function normalizeError(error: unknown) {
    if (!error) {
        return undefined;
    }

    if (error instanceof Error) {
        return {
            name: error.name,
            message: error.message,
            stack: error.stack,
        };
    }

    if (typeof error === 'object') {
        return error;
    }

    return { message: String(error) };
}

function shouldEmit(level: LogLevel) {
    return APP_ENVIRONMENT === 'development' || level === 'warn' || level === 'error';
}

function writeLog(level: LogLevel, logger: string, message: string, fields: LogFields = {}, error?: unknown) {
    if (!shouldEmit(level)) {
        return;
    }

    const payload = {
        timestamp: new Date().toISOString(),
        level,
        logger,
        message,
        'service.name': SERVICE_NAME,
        'service.namespace': SERVICE_NAMESPACE,
        'deployment.environment': APP_ENVIRONMENT,
        client_session_id: getClientSessionId(),
        ...fields,
        error: normalizeError(error),
    };

    const serialized = JSON.stringify(payload);
    if (level === 'error') {
        console.error(serialized);
        return;
    }

    if (level === 'warn') {
        console.warn(serialized);
        return;
    }

    if (level === 'info') {
        console.info(serialized);
        return;
    }

    console.debug(serialized);
}

export function createRequestId() {
    return generateId();
}

export function getClientSessionId() {
    if (cachedSessionId) {
        return cachedSessionId;
    }

    const storage = getStorage();
    if (!storage) {
        cachedSessionId = generateId();
        return cachedSessionId;
    }

    const existing = storage.getItem(CLIENT_SESSION_STORAGE_KEY);
    if (existing) {
        cachedSessionId = existing;
        return cachedSessionId;
    }

    cachedSessionId = generateId();
    storage.setItem(CLIENT_SESSION_STORAGE_KEY, cachedSessionId);
    return cachedSessionId;
}

export function createLogger(name: string) {
    return {
        debug(message: string, fields?: LogFields) {
            writeLog('debug', name, message, fields);
        },
        info(message: string, fields?: LogFields) {
            writeLog('info', name, message, fields);
        },
        warn(message: string, fields?: LogFields, error?: unknown) {
            writeLog('warn', name, message, fields, error);
        },
        error(message: string, fields?: LogFields, error?: unknown) {
            writeLog('error', name, message, fields, error);
        },
    };
}

export const appLogger = createLogger('VFR.Web');
