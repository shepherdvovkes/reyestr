import { useQuery } from '@tanstack/react-query'
import { Box, Grid, Paper, Typography, Card, CardContent } from '@mui/material'
import {
  Assignment as TaskIcon,
  Computer as ClientIcon,
  CheckCircle as CompletedIcon,
  Error as ErrorIcon,
} from '@mui/icons-material'
import { tasksApi } from '../api/tasks'
import { clientsApi } from '../api/clients'

export default function DashboardPage() {
  const { data: tasksSummary } = useQuery({
    queryKey: ['tasks', 'summary'],
    queryFn: () => tasksApi.getSummary(),
    refetchInterval: 5000,
  })

  const { data: clients } = useQuery({
    queryKey: ['clients'],
    queryFn: () => clientsApi.getAll(),
    refetchInterval: 5000,
  })

  const activeClients = clients?.filter((c) => c.status === 'active').length || 0

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>

      <Grid container spacing={3} sx={{ mt: 2 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <TaskIcon sx={{ mr: 1, color: 'primary.main' }} />
                <Typography color="textSecondary" gutterBottom>
                  Total Tasks
                </Typography>
              </Box>
              <Typography variant="h4">{tasksSummary?.total_tasks || 0}</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <CompletedIcon sx={{ mr: 1, color: 'success.main' }} />
                <Typography color="textSecondary" gutterBottom>
                  Completed
                </Typography>
              </Box>
              <Typography variant="h4">{tasksSummary?.completed || 0}</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <ErrorIcon sx={{ mr: 1, color: 'error.main' }} />
                <Typography color="textSecondary" gutterBottom>
                  Failed
                </Typography>
              </Box>
              <Typography variant="h4">{tasksSummary?.failed || 0}</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <ClientIcon sx={{ mr: 1, color: 'info.main' }} />
                <Typography color="textSecondary" gutterBottom>
                  Active Clients
                </Typography>
              </Box>
              <Typography variant="h4">{activeClients}</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Task Status Overview
            </Typography>
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={6} sm={3}>
                <Typography variant="body2" color="textSecondary">
                  Pending
                </Typography>
                <Typography variant="h5">{tasksSummary?.pending || 0}</Typography>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Typography variant="body2" color="textSecondary">
                  Assigned
                </Typography>
                <Typography variant="h5">{tasksSummary?.assigned || 0}</Typography>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Typography variant="body2" color="textSecondary">
                  In Progress
                </Typography>
                <Typography variant="h5">{tasksSummary?.in_progress || 0}</Typography>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Typography variant="body2" color="textSecondary">
                  Completed
                </Typography>
                <Typography variant="h5">{tasksSummary?.completed || 0}</Typography>
              </Grid>
            </Grid>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}
