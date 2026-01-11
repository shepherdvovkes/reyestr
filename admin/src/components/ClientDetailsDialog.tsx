import { useQuery } from '@tanstack/react-query'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Grid,
  Paper,
  Chip,
  List,
  ListItem,
  ListItemText,
  CircularProgress,
  Alert,
  Divider,
} from '@mui/material'
import { formatDistanceToNow } from 'date-fns'
import { clientsApi, ClientActivity } from '../api/clients'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface ClientDetailsDialogProps {
  open: boolean
  onClose: () => void
  clientId: string
}

export default function ClientDetailsDialog({ open, onClose, clientId }: ClientDetailsDialogProps) {
  const { data: activity, isLoading, error } = useQuery<ClientActivity>({
    queryKey: ['clients', clientId, 'activity'],
    queryFn: () => clientsApi.getActivity(clientId),
    enabled: open,
    refetchInterval: 2000,
  })

  if (isLoading) {
    return (
      <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
        <DialogContent>
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        </DialogContent>
      </Dialog>
    )
  }

  if (error || !activity) {
    return (
      <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
        <DialogContent>
          <Alert severity="error">Failed to load client activity</Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Close</Button>
        </DialogActions>
      </Dialog>
    )
  }

  const speedData = activity.current_task
    ? [
        {
          time: 'Now',
          speed: activity.current_task.speed_docs_per_minute,
        },
      ]
    : []

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>Client Activity Monitor</DialogTitle>
      <DialogContent>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2, mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                Current Task
              </Typography>
              {activity.current_task ? (
                <Box>
                  <Typography variant="body2" color="textSecondary">
                    Task ID: {activity.current_task.task_id}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Status: {activity.current_task.status}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Speed: {activity.current_task.speed_docs_per_minute.toFixed(2)} docs/min
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Downloaded: {activity.current_task.documents_downloaded} /{' '}
                    {activity.current_task.max_documents}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Failed: {activity.current_task.documents_failed}
                  </Typography>
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2" fontWeight="bold">
                      Search Params:
                    </Typography>
                    <Typography variant="body2" component="pre" sx={{ fontSize: '0.75rem' }}>
                      {JSON.stringify(activity.current_task.search_params, null, 2)}
                    </Typography>
                  </Box>
                </Box>
              ) : (
                <Typography color="textSecondary">No active task</Typography>
              )}
            </Paper>

            <Paper sx={{ p: 2, mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                Session Statistics
              </Typography>
              <Typography variant="body2">
                Documents Downloaded: {activity.session_stats.documents_downloaded}
              </Typography>
              <Typography variant="body2">
                Tasks Completed: {activity.session_stats.tasks_completed}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Started:{' '}
                {formatDistanceToNow(new Date(activity.session_stats.start_time), { addSuffix: true })}
              </Typography>
            </Paper>

            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Lifetime Statistics
              </Typography>
              <Typography variant="body2">
                Total Documents: {activity.lifetime_stats.total_documents}
              </Typography>
              <Typography variant="body2">
                Total Tasks: {activity.lifetime_stats.total_tasks}
              </Typography>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2, mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                Download Speed
              </Typography>
              {speedData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={speedData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" />
                    <YAxis />
                    <Tooltip />
                    <Line type="monotone" dataKey="speed" stroke="#8884d8" />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <Typography color="textSecondary">No data available</Typography>
              )}
            </Paper>

            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Recent Errors
              </Typography>
              {activity.errors.length > 0 ? (
                <List dense>
                  {activity.errors.slice(0, 5).map((error) => (
                    <ListItem key={error.id} divider>
                      <ListItemText
                        primary={error.error_message}
                        secondary={formatDistanceToNow(new Date(error.timestamp), { addSuffix: true })}
                      />
                    </ListItem>
                  ))}
                </List>
              ) : (
                <Typography color="textSecondary">No errors</Typography>
              )}
            </Paper>
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  )
}
