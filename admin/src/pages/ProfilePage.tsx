import React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Box,
  Typography,
  Paper,
  TextField,
  Button,
  Grid,
  Alert,
  CircularProgress,
} from '@mui/material'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { usersApi, UpdateUserRequest } from '../api/users'

const profileSchema = z.object({
  display_name: z.string().min(1, 'Display name is required'),
  email: z.string().email('Invalid email').optional().or(z.literal('')),
  telegram_chat_id: z.string().optional().or(z.literal('')),
})

type ProfileFormData = z.infer<typeof profileSchema>

export default function ProfilePage() {
  const queryClient = useQueryClient()

  const { data: user, isLoading } = useQuery({
    queryKey: ['user', 'profile'],
    queryFn: () => usersApi.getProfile(),
  })

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      display_name: user?.display_name || '',
      email: user?.email || '',
      telegram_chat_id: user?.telegram_chat_id || '',
    },
  })

  // Update form when user data loads
  React.useEffect(() => {
    if (user) {
      reset({
        display_name: user.display_name,
        email: user.email || '',
        telegram_chat_id: user.telegram_chat_id || '',
      })
    }
  }, [user, reset])

  const updateMutation = useMutation({
    mutationFn: (data: UpdateUserRequest) => usersApi.updateProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user', 'profile'] })
    },
  })

  const onSubmit = async (data: ProfileFormData) => {
    try {
      await updateMutation.mutateAsync({
        display_name: data.display_name,
        email: data.email || undefined,
        telegram_chat_id: data.telegram_chat_id || undefined,
      })
    } catch (error) {
      console.error('Failed to update profile:', error)
    }
  }

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Profile Settings
      </Typography>

      <Paper sx={{ p: 3, mt: 3 }}>
        <form onSubmit={handleSubmit(onSubmit)}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Username"
                value={user?.username || ''}
                disabled
                helperText="Username cannot be changed"
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Display Name"
                {...register('display_name')}
                error={!!errors.display_name}
                helperText={errors.display_name?.message}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Email"
                type="email"
                {...register('email')}
                error={!!errors.email}
                helperText={errors.email?.message}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Telegram Chat ID"
                {...register('telegram_chat_id')}
                error={!!errors.telegram_chat_id}
                helperText={
                  errors.telegram_chat_id?.message ||
                  'Your Telegram chat ID for receiving critical error notifications'
                }
              />
            </Grid>

            {updateMutation.isSuccess && (
              <Grid item xs={12}>
                <Alert severity="success">Profile updated successfully</Alert>
              </Grid>
            )}

            {updateMutation.isError && (
              <Grid item xs={12}>
                <Alert severity="error">
                  Failed to update profile. Please try again.
                </Alert>
              </Grid>
            )}

            <Grid item xs={12}>
              <Button
                type="submit"
                variant="contained"
                disabled={isSubmitting}
                sx={{ minWidth: 120 }}
              >
                {isSubmitting ? <CircularProgress size={24} /> : 'Save Changes'}
              </Button>
            </Grid>
          </Grid>
        </form>
      </Paper>
    </Box>
  )
}
