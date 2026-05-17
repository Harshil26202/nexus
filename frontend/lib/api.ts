import axios from "axios";

export const api = axios.create({
  baseURL: "/api/backend",
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      window.location.href = "/auth/signin";
    }
    return Promise.reject(err);
  }
);
