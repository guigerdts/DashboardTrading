import { Component } from 'react';
import { ErrorFallback } from './ErrorFallback';

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <ErrorFallback
            message="Something went wrong loading this section."
            onRetry={this.handleRetry}
          />
        )
      );
    }
    return this.props.children;
  }
}
