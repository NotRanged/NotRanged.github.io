# syntax=docker/dockerfile:1

FROM node:16.13.1
ENV NODE_ENV=production
WORKDIR /app
COPY ["package.json", "./"]
RUN npm install --production
COPY . .
CMD [ "node", "server.js" ]