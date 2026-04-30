FROM node:16-alpine

WORKDIR /app

# Instala dependencias
COPY package*.json ./
RUN npm install

# Copia el resto y arranca el servidor de desarrollo
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
