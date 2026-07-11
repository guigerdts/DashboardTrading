import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EdgeStabilityIndicator } from '../EdgeStabilityIndicator';

describe('EdgeStabilityIndicator', () => {
  it('renders "High" label for high confidence', () => {
    render(<EdgeStabilityIndicator stability={0.95} confidenceLevel="high" />);
    expect(screen.getByText('High')).toBeInTheDocument();
  });

  it('renders "Medium" label for medium confidence', () => {
    render(<EdgeStabilityIndicator stability={0.7} confidenceLevel="medium" />);
    expect(screen.getByText('Medium')).toBeInTheDocument();
  });

  it('renders "Low" label for low confidence', () => {
    render(<EdgeStabilityIndicator stability={0.4} confidenceLevel="low" />);
    expect(screen.getByText('Low')).toBeInTheDocument();
  });

  it('renders "Insufficient" label for insufficient confidence', () => {
    render(<EdgeStabilityIndicator stability={0.1} confidenceLevel="insufficient" />);
    expect(screen.getByText('Insufficient')).toBeInTheDocument();
  });

  it('shows stability percentage in title attribute', () => {
    render(<EdgeStabilityIndicator stability={0.856} confidenceLevel="high" />);
    const el = screen.getByText('High');
    expect(el).toHaveAttribute('title', 'Stability: 86%');
  });

  it('renders with green dot for high confidence', () => {
    const { container } = render(
      <EdgeStabilityIndicator stability={0.9} confidenceLevel="high" />,
    );
    const dot = container.querySelector('span > span');
    expect(dot.className).toContain('bg-green-500');
  });

  it('renders with yellow dot for medium confidence', () => {
    const { container } = render(
      <EdgeStabilityIndicator stability={0.6} confidenceLevel="medium" />,
    );
    const dot = container.querySelector('span > span');
    expect(dot.className).toContain('bg-yellow-400');
  });

  it('renders with gray dot for low confidence', () => {
    const { container } = render(
      <EdgeStabilityIndicator stability={0.3} confidenceLevel="low" />,
    );
    const dot = container.querySelector('span > span');
    expect(dot.className).toContain('bg-gray-400');
  });

  it('renders with red dot for insufficient confidence', () => {
    const { container } = render(
      <EdgeStabilityIndicator stability={0.05} confidenceLevel="insufficient" />,
    );
    const dot = container.querySelector('span > span');
    expect(dot.className).toContain('bg-red-400');
  });

  it('falls back to insufficient for unknown confidenceLevel', () => {
    render(<EdgeStabilityIndicator stability={0} confidenceLevel="unknown" />);
    expect(screen.getByText('Insufficient')).toBeInTheDocument();
  });
});
