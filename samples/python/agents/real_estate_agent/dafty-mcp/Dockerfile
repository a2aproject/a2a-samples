# Use an official Node.js runtime as a parent image for building
FROM node:22-alpine AS builder

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy package.json and package-lock.json to the working directory
COPY package*.json ./

# Install all dependencies and build the TypeScript source
RUN npm ci
COPY . .
RUN npm run build

# Start a new, clean stage for the production image
FROM node:22-alpine

# Set the working directory
WORKDIR /usr/src/app

# Copy package files and install only production dependencies
COPY package*.json ./
RUN npm ci --omit=dev

# Install curl for health checks
RUN apk add --no-cache curl

# Copy the built application from the builder stage
COPY --from=builder /usr/src/app/build ./build

# Create logs directory and set ownership before switching user
RUN mkdir -p logs && chown node:node logs

# Switch to the non-root user
USER node

# Your app binds to port 4000, so expose that
EXPOSE 4000

# Define the command to run your app
CMD [ "npm", "start" ]