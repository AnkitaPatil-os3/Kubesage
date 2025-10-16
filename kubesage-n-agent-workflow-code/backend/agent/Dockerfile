# Build stage
FROM golang:1.21-alpine AS builder

# Set working directory
WORKDIR /app

# Install git and ca-certificates
RUN apk add --no-cache git ca-certificates

# Copy go mod and sum files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o kubesage-agent .

# Final stage
FROM alpine:latest

# Install ca-certificates for HTTPS calls
RUN apk --no-cache add ca-certificates

# Create non-root user
RUN adduser -D -s /bin/sh kubesage

WORKDIR /home/kubesage

# Copy the binary from builder stage
COPY --from=builder /app/kubesage-agent .

# Change ownership
RUN chown kubesage:kubesage kubesage-agent

# Switch to non-root user
USER kubesage

# Expose port
EXPOSE 9000

# Run the application
CMD ["./kubesage-agent"]