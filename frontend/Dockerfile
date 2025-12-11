FROM node:20-alpine

WORKDIR /app

# Expose port
EXPOSE 3000

# Install, build, and run at runtime (avoids build issues in LXC)
CMD npm install && npm run build && npm start
