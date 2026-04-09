# 🌐 TranslateHub - Guía de Despliegue

## Arquitectura de Producción

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  Cloudflare Pages   │────▶│  Backend API         │────▶│    MongoDB      │
│  (Frontend React)   │     │  (Clouding.io/Render)│     │  (Atlas/Local)  │
└─────────────────────┘     └──────────────────────┘     └─────────────────┘
```

---

## 📦 Opción 1: Backend en Clouding.io + Frontend en Cloudflare

### Paso 1: Configurar MongoDB

**Opción A: MongoDB Atlas (Recomendado - Gratis)**
1. Ve a [mongodb.com/atlas](https://www.mongodb.com/atlas)
2. Crea una cuenta gratuita
3. Crea un cluster (M0 Free Tier)
4. En "Network Access" → Add IP Address → Allow Access from Anywhere
5. En "Database Access" → Crea un usuario con password
6. Obtén tu connection string: `mongodb+srv://usuario:password@cluster.xxxxx.mongodb.net/translatehub`

### Paso 2: Desplegar Backend en Clouding.io

1. **Accede a [clouding.io](https://clouding.io)** y crea una cuenta

2. **Crea un servidor**:
   - SO: Ubuntu 22.04 LTS
   - Plan: Mínimo 1 CPU, 2GB RAM
   - Ubicación: Madrid (o la más cercana)

3. **Conéctate por SSH**:
   ```bash
   ssh root@tu-ip-servidor
   ```

4. **Instala Docker**:
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER
   ```

5. **Clona tu repositorio** (o sube los archivos):
   ```bash
   git clone https://github.com/tu-usuario/translatehub.git
   cd translatehub
   ```

6. **Configura las variables de entorno**:
   ```bash
   cd backend
   cp .env.example .env
   nano .env
   ```
   
   Edita con tus valores:
   ```env
   MONGO_URL=mongodb+srv://usuario:password@cluster.xxxxx.mongodb.net/translatehub
   DB_NAME=translatehub
   CORS_ORIGINS=https://tu-app.pages.dev
   EMERGENT_LLM_KEY=sk-emergent-xxxxx
   ```

7. **Construye y ejecuta con Docker**:
   ```bash
   docker build -t translatehub-backend .
   docker run -d --name translatehub -p 8001:8001 --env-file .env translatehub-backend
   ```

8. **Configura Nginx como proxy** (opcional pero recomendado):
   ```bash
   apt install nginx certbot python3-certbot-nginx -y
   ```
   
   Crea `/etc/nginx/sites-available/translatehub`:
   ```nginx
   server {
       server_name api.tudominio.com;
       
       location / {
           proxy_pass http://localhost:8001;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_cache_bypass $http_upgrade;
           client_max_body_size 100M;
       }
   }
   ```
   
   ```bash
   ln -s /etc/nginx/sites-available/translatehub /etc/nginx/sites-enabled/
   nginx -t && systemctl reload nginx
   certbot --nginx -d api.tudominio.com
   ```

9. **Tu API estará en**: `https://api.tudominio.com/api/`

### Paso 3: Desplegar Frontend en Cloudflare Pages

1. **Ve a [pages.cloudflare.com](https://pages.cloudflare.com)**

2. **Conecta tu repositorio de GitHub**:
   - Haz push de tu código a GitHub primero
   - En Cloudflare: "Create a project" → "Connect to Git"

3. **Configura el build**:
   - Framework preset: `Create React App`
   - Build command: `yarn build`
   - Build output directory: `build`
   - Root directory: `frontend`

4. **Configura las variables de entorno**:
   - `REACT_APP_BACKEND_URL` = `https://api.tudominio.com` (tu backend de Clouding.io)

5. **Deploy** y espera a que termine

6. **Tu frontend estará en**: `https://tu-proyecto.pages.dev`

---

## 📦 Opción 2: Backend en Render + Frontend en Cloudflare

### Paso 1: Desplegar Backend en Render

1. **Ve a [render.com](https://render.com)** y crea una cuenta

2. **Nuevo Web Service**:
   - Conecta tu repositorio de GitHub
   - Root Directory: `backend`
   - Runtime: `Python 3`
   - Build Command: 
     ```
     pip install -r requirements.txt
     ```
   - Start Command: 
     ```
     uvicorn server:app --host 0.0.0.0 --port $PORT
     ```

3. **Variables de entorno** (en dashboard de Render):
   ```
   MONGO_URL=mongodb+srv://...
   DB_NAME=translatehub
   CORS_ORIGINS=https://tu-app.pages.dev
   EMERGENT_LLM_KEY=sk-emergent-xxxxx
   ```

4. **Nota**: Render tiene plan gratuito pero con limitaciones. El servicio se "duerme" después de 15 min de inactividad.

5. **Tu API estará en**: `https://translatehub-api.onrender.com/api/`

### Paso 2: Frontend en Cloudflare (igual que arriba)

Usa la URL de Render como `REACT_APP_BACKEND_URL`.

---

## 🔧 Comandos Útiles

### Docker (Clouding.io)
```bash
# Ver logs
docker logs -f translatehub

# Reiniciar
docker restart translatehub

# Actualizar
docker stop translatehub
docker rm translatehub
docker build -t translatehub-backend .
docker run -d --name translatehub -p 8001:8001 --env-file .env translatehub-backend
```

### Verificar API
```bash
curl https://tu-api-url/api/
# Debe responder: {"message":"Translation API is running"}

curl https://tu-api-url/api/languages
# Debe responder: lista de 50 idiomas
```

---

## ⚠️ Notas Importantes

1. **CORS**: Asegúrate de que `CORS_ORIGINS` en el backend incluya la URL exacta de tu frontend en Cloudflare.

2. **MongoDB**: Si usas MongoDB Atlas, asegúrate de permitir conexiones desde la IP de tu servidor (o "Allow from Anywhere" para testing).

3. **OCR en Render**: Render puede tener limitaciones con Tesseract OCR. Si tienes problemas, Clouding.io con Docker es más flexible.

4. **Archivos temporales**: Los archivos traducidos se guardan en `/tmp/translate_app`. En servicios como Render, estos se borran al reiniciar.

5. **Límites de archivos**: Configura `client_max_body_size` en Nginx si usas archivos grandes.

---

## 📞 Soporte

Si tienes problemas:
1. Verifica los logs del backend
2. Comprueba que las variables de entorno estén correctas
3. Asegúrate de que CORS esté bien configurado
