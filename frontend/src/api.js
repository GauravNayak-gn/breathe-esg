const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
let csrfTokenCache = null;

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

async function getCsrfToken() {
  const cookieToken = getCookie('csrftoken');
  if (cookieToken) {
    csrfTokenCache = cookieToken;
    return cookieToken;
  }

  if (csrfTokenCache) return csrfTokenCache;

  const response = await fetch(`${BASE_URL}/api/auth/csrf/`, {
    credentials: 'include',
  });

  if (!response.ok) return null;

  const data = await response.json().catch(() => ({}));
  csrfTokenCache = data.csrfToken || getCookie('csrftoken');
  return csrfTokenCache;
}

async function cacheCsrfTokenFromResponse(response) {
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) return;

  const data = await response.clone().json().catch(() => ({}));
  if (data.csrfToken) {
    csrfTokenCache = data.csrfToken;
  }
}

export async function apiFetch(url, options = {}) {
  const fullUrl = url.startsWith('http') ? url : `${BASE_URL}${url}`;

  const headers = {
    ...options.headers,
  };

  if (options.method === 'POST' || options.method === 'PUT' || options.method === 'PATCH' || options.method === 'DELETE') {
    const csrfToken = await getCsrfToken();
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }
  }

  const response = await fetch(fullUrl, {
    credentials: 'include',
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    if (response.status === 401) {
      window.location.href = '/login';
    }
    throw new Error(errorData.error || `Request failed with status ${response.status}`);
  }

  await cacheCsrfTokenFromResponse(response);

  return response;
}

export const api = {
  auth: {
    getCsrf: () => apiFetch('/api/auth/csrf/'),
    login: (formData) => apiFetch('/api/auth/login/', {
      method: 'POST',
      body: formData, // FormData or URLSearchParams as requested
    }),
    logout: () => apiFetch('/api/auth/logout/', { method: 'POST' }),
  },
  dashboard: {
    getSummary: () => apiFetch('/api/dashboard/').then(r => r.json()),
  },
  ingest: {
    uploadSap: (file) => {
      const fd = new FormData();
      fd.append('file', file);
      return apiFetch('/api/ingest/sap/', { method: 'POST', body: fd });
    },
    uploadUtility: (file) => {
      const fd = new FormData();
      fd.append('file', file);
      return apiFetch('/api/ingest/utility/', { method: 'POST', body: fd });
    },
    uploadTravel: (file) => {
      const fd = new FormData();
      fd.append('file', file);
      return apiFetch('/api/ingest/travel/', { method: 'POST', body: fd });
    },
  },
  emissions: {
    list: (params = {}) => {
      const query = new URLSearchParams(params).toString();
      return apiFetch(`/api/emissions/${query ? `?${query}` : ''}`).then(r => r.json());
    },
    get: (id) => apiFetch(`/api/emissions/${id}/`).then(r => r.json()),
    approve: (id) => apiFetch(`/api/emissions/${id}/approve/`, { method: 'POST' }),
    reject: (id, note) => apiFetch(`/api/emissions/${id}/reject/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note }),
    }),
    lock: (id) => apiFetch(`/api/emissions/${id}/lock/`, { method: 'POST' }),
  }
};
