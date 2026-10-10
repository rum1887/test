import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  tabName?: string;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error in tab:', this.props.tabName, error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="card" style={{ padding: 32, margin: '24px 0', textAlign: 'center' }}>
          <div style={{ fontSize: 28, marginBottom: 12 }}>⚠️</div>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
            Unable to display {this.props.tabName || 'this view'}
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 20 }}>
            {this.state.error?.message || 'An unexpected rendering error occurred.'}
          </p>
          <button
            className="btn btn-primary btn-sm"
            onClick={() => this.setState({ hasError: false, error: undefined })}
          >
            Retry View
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
