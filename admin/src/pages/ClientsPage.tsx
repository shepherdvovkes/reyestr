import { useQuery } from '@tanstack/react-query'
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Tooltip,
} from '@mui/material'
import {
  Refresh as RefreshIcon,
  Info as InfoIcon,
} from '@mui/icons-material'
import { formatDistanceToNow } from 'date-fns'
import { clientsApi, Client } from '../api/clients'
import ClientDetailsDialog from '../components/ClientDetailsDialog'
import { useState } from 'react'

export default function ClientsPage() {
  const [selectedClient, setSelectedClient] = useState<Client | null>(null)
  const [detailsOpen, setDetailsOpen] = useState(false)

  const { data: clients, isLoading, refetch } = useQuery({
    queryKey: ['clients'],
    queryFn: () => clientsApi.getAll(),
    refetchInterval: 5000,
  })

  const handleViewDetails = (client: Client) => {
    setSelectedClient(client)
    setDetailsOpen(true)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success'
      case 'inactive':
        return 'default'
      case 'error':
        return 'error'
      default:
        return 'default'
    }
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Clients</Typography>
        <IconButton onClick={() => refetch()}>
          <RefreshIcon />
        </IconButton>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Host</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Last Heartbeat</TableCell>
              <TableCell>Tasks Completed</TableCell>
              <TableCell>Documents Downloaded</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  Loading...
                </TableCell>
              </TableRow>
            ) : clients && clients.length > 0 ? (
              clients.map((client) => (
                <TableRow key={client.id} hover>
                  <TableCell>{client.client_name}</TableCell>
                  <TableCell>{client.client_host || '-'}</TableCell>
                  <TableCell>
                    <Chip
                      label={client.status}
                      color={getStatusColor(client.status) as any}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {client.last_heartbeat
                      ? formatDistanceToNow(new Date(client.last_heartbeat), { addSuffix: true })
                      : 'Never'}
                  </TableCell>
                  <TableCell>{client.total_tasks_completed}</TableCell>
                  <TableCell>{client.total_documents_downloaded}</TableCell>
                  <TableCell>
                    <Tooltip title="View Details">
                      <IconButton size="small" onClick={() => handleViewDetails(client)}>
                        <InfoIcon />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  No clients found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {selectedClient && (
        <ClientDetailsDialog
          open={detailsOpen}
          onClose={() => {
            setDetailsOpen(false)
            setSelectedClient(null)
          }}
          clientId={selectedClient.id}
        />
      )}
    </Box>
  )
}
