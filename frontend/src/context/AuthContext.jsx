import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { getAuthToken, setAuthToken, loginUser, getCurrentUser, logoutUser } from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => getAuthToken())
  const [isLoading, setIsLoading] = useState(true)

  // Verify stored token on initial mount
  useEffect(() => {
    let isMounted = true
    const existingToken = getAuthToken()

    if (!existingToken) {
      setIsLoading(false)
      return
    }

    getCurrentUser()
      .then((data) => {
        if (isMounted) {
          if (data && data.authenticated && data.user) {
            setUser(data.user)
            setToken(existingToken)
          } else {
            setAuthToken(null)
            setUser(null)
            setToken(null)
          }
        }
      })
      .catch((err) => {
        // If 401 or invalid token, purge it
        if (isMounted) {
          if (err && (err.status === 401 || err.status === 403)) {
            setAuthToken(null)
            setUser(null)
            setToken(null)
          } else {
            // If offline/network failure, keep token but mark user as guest or unverified
            // To ensure safety, if not verified we clear token
            setAuthToken(null)
            setUser(null)
            setToken(null)
          }
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [])

  const login = useCallback(async (username, password) => {
    const data = await loginUser(username, password)
    if (data && data.token && data.user) {
      setAuthToken(data.token)
      setToken(data.token)
      setUser(data.user)
      return data.user
    }
    throw new Error('Respons autentikasi tidak valid dari server.')
  }, [])

  const logout = useCallback(async () => {
    try {
      await logoutUser()
    } catch {
      // Ignore network errors on logout
    } finally {
      setAuthToken(null)
      setToken(null)
      setUser(null)
    }
  }, [])

  const value = {
    user,
    token,
    isLoading,
    isAuthenticated: Boolean(user && token),
    login,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth harus digunakan di dalam <AuthProvider>')
  }
  return context
}

