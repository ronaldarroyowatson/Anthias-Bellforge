import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { SystemInfo } from '@/components/system-info'
import { createMockServer } from '@/tests/utils'

const server = createMockServer()

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('SystemInfo', () => {
  it('should not show the bell overlay and should show system info table', async () => {
    render(<SystemInfo />)
    // Bell/logo should not be present
    expect(screen.queryByAltText(/bellforge logo/i)).not.toBeInTheDocument()
    // System info table should be visible
    expect(screen.getByRole('table')).toBeVisible()
    expect(screen.getByText('System Info')).toBeVisible()
  })
  it('renders the system info', async () => {
    render(<SystemInfo />)

    expect(screen.getByRole('heading')).toHaveTextContent('System Info')

    expect(screen.getByText('Load Average')).toBeInTheDocument()
    expect(screen.getByText('Free Space')).toBeInTheDocument()
    expect(screen.getByText('Memory')).toBeInTheDocument()
    expect(screen.getByText('Uptime')).toBeInTheDocument()
    expect(screen.getByText('Display Power (CEC)')).toBeInTheDocument()
    expect(screen.getByText('Device Model')).toBeInTheDocument()
    expect(screen.getByText('Anthias Version')).toBeInTheDocument()
    expect(screen.getByText('MAC Address')).toBeInTheDocument()

    const expectedValues = [
      '1.58',
      '31G',
      'CEC error',
      '8 days and 18.56 hours',
      'Generic x86_64 Device',
      'master@3a4747f',
      'Unable to retrieve MAC address.',
    ]

    for (const value of expectedValues) {
      const element = await screen.findByText(value)
      expect(element).toBeInTheDocument()
    }
  })
})
