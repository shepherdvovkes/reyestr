import { useQuery } from '@tanstack/react-query'
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material'
import { tasksApi, TaskIndex, Task } from '../api/tasks'
import { useState } from 'react'

const COURT_REGIONS: Record<string, string> = {
  '11': 'Київська область',
  '14': 'Львівська область',
  // Add more regions as needed
}

const INSTANCE_TYPES: Record<string, string> = {
  '1': 'Перша інстанція',
  '2': 'Апеляційна',
  '3': 'Касаційна',
}

export default function TasksMapPage() {
  const [selectedIndex, setSelectedIndex] = useState<TaskIndex | null>(null)
  const [tasks, setTasks] = useState<Task[]>([])
  const [dialogOpen, setDialogOpen] = useState(false)

  const { data: indexes, isLoading } = useQuery({
    queryKey: ['tasks', 'indexes'],
    queryFn: () => tasksApi.getIndexes(),
    refetchInterval: 10000,
  })

  const handleIndexClick = async (index: TaskIndex) => {
    setSelectedIndex(index)
    try {
      const indexTasks = await tasksApi.getByIndex(
        index.court_region,
        index.instance_type,
        index.date_range.start,
        index.date_range.end
      )
      setTasks(indexTasks)
      setDialogOpen(true)
    } catch (error) {
      console.error('Failed to load tasks:', error)
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Tasks Map
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Navigate through task indexes by region, instance type, and date range
      </Typography>

      {isLoading ? (
        <Typography>Loading indexes...</Typography>
      ) : indexes && indexes.length > 0 ? (
        <Grid container spacing={2}>
          {indexes.map((index, idx) => (
            <Grid item xs={12} sm={6} md={4} key={idx}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    {COURT_REGIONS[index.court_region] || `Region ${index.court_region}`}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {INSTANCE_TYPES[index.instance_type] || `Type ${index.instance_type}`}
                  </Typography>
                  <Box sx={{ my: 2 }}>
                    <Typography variant="body2">
                      {new Date(index.date_range.start).toLocaleDateString()} -{' '}
                      {new Date(index.date_range.end).toLocaleDateString()}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                    <Chip
                      label={`Total: ${index.total_tasks}`}
                      size="small"
                      color="primary"
                      variant="outlined"
                    />
                    <Chip
                      label={`Completed: ${index.completed_tasks}`}
                      size="small"
                      color="success"
                      variant="outlined"
                    />
                    <Chip
                      label={`Pending: ${index.pending_tasks}`}
                      size="small"
                      color="warning"
                      variant="outlined"
                    />
                    {index.failed_tasks > 0 && (
                      <Chip
                        label={`Failed: ${index.failed_tasks}`}
                        size="small"
                        color="error"
                        variant="outlined"
                      />
                    )}
                  </Box>
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => handleIndexClick(index)}
                  >
                    View Tasks
                  </Button>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      ) : (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography color="text.secondary">No task indexes available</Typography>
        </Paper>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="lg" fullWidth>
        <DialogTitle>
          Tasks: {selectedIndex && COURT_REGIONS[selectedIndex.court_region]} -{' '}
          {selectedIndex && INSTANCE_TYPES[selectedIndex.instance_type]}
        </DialogTitle>
        <DialogContent>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Task ID</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Start Page</TableCell>
                  <TableCell>Max Documents</TableCell>
                  <TableCell>Downloaded</TableCell>
                  <TableCell>Failed</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {tasks.map((task) => (
                  <TableRow key={task.task_id}>
                    <TableCell>{task.task_id.substring(0, 8)}...</TableCell>
                    <TableCell>
                      <Chip label={task.status} size="small" />
                    </TableCell>
                    <TableCell>{task.start_page}</TableCell>
                    <TableCell>{task.max_documents}</TableCell>
                    <TableCell>{task.documents_downloaded}</TableCell>
                    <TableCell>{task.documents_failed}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
