# Frontend Dockerfile for React + TypeScript (Node 18)
FROM node:18-alpine

RUN apk add --no-cache curl

WORKDIR /usr/src/app

COPY package.json package-lock.json* .npmrc* ./
RUN npm install --legacy-peer-deps || yarn install || pnpm install || true

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
