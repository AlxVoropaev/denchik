import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { auth } from "../api/endpoints";
import { useAuthStore } from "../store/auth";

export function useMe() {
  const setUser = useAuthStore((s) => s.setUser);
  return useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      console.debug("[useMe] fetching /auth/me");
      try {
        const u = await auth.me();
        console.debug("[useMe] success", u);
        setUser(u);
        return u;
      } catch (e) {
        console.debug("[useMe] failed (likely 401)", e);
        throw e;
      }
    },
    retry: false,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      auth.login(email, password),
    onSuccess: (u) => {
      setUser(u);
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export function useRegister() {
  const qc = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);
  return useMutation({
    mutationFn: ({ email, password, display_name }: { email: string; password: string; display_name: string }) =>
      auth.register(email, password, display_name),
    onSuccess: (u) => {
      setUser(u);
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);
  return useMutation({
    mutationFn: () => auth.logout(),
    onSuccess: () => {
      setUser(null);
      qc.clear();
    },
  });
}
