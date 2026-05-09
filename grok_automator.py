import os
import asyncio
import time
from playwright.async_api import async_playwright

async def generate_videos_in_grok(image_folder, output_folder, prompts_dict=None):
    """
    Automates Grok to convert images to videos.
    """
    user_data_dir = os.path.join(os.getcwd(), 'playwright_data_grok')
    os.makedirs(user_data_dir, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)

    print(f"[GrokAutomator] Iniciando Playwright para Grok...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            channel="chrome", 
            viewport={'width': 1280, 'height': 800},
            ignore_default_args=["--enable-automation"],
            args=['--start-maximized', '--disable-blink-features=AutomationControlled']
        )
        
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        print(f"[GrokAutomator] Verificando sesión en Grok...")
        await page.goto('https://grok.com/imagine')
        grok_input = page.locator('textarea, div[contenteditable="true"]').first
        try:
            await grok_input.wait_for(state="visible", timeout=10000)
            print("[GrokAutomator] [OK] Sesión detectada.")
        except:
            print("\n=======================================================")
            print("[INFO] NECESITAS INICIAR SESIÓN EN GROK")
            print("El bot se pausará hasta que loguees y aparezca la caja de texto (max 5 min)...")
            await grok_input.wait_for(state="visible", timeout=300000)
            print("[GrokAutomator] [OK] Sesión detectada. Continuamos.\n")
            
        expected_ids = list(prompts_dict.keys()) if prompts_dict else []
        if not expected_ids:
            # Fallback si se ejecuta de forma independiente y no hay prompts
            images = [f for f in os.listdir(image_folder) if f.endswith(('.png', '.jpg'))]
            expected_ids = [f.split('.')[0] for f in images]

        if not expected_ids:
            print("[GrokAutomator] No hay imágenes esperadas para animar.")
            await browser.close()
            return
            
        print(f"[GrokAutomator] Procesando {len(expected_ids)} imágenes...")
        
        # 1. Crear y entrar a una etiqueta para el proyecto
        project_label = f"Proyecto_{int(time.time())}"
        if prompts_dict and len(prompts_dict) > 0:
            first_prompt = list(prompts_dict.values())[0]
            # Limpiar caracteres raros y tomar hasta 5 palabras
            clean_text = "".join([c for c in first_prompt if c.isalnum() or c.isspace()])
            words = clean_text.split()[:5]
            if words:
                # Grok tiene un límite de 64 caracteres para las etiquetas
                project_label = " ".join(words).strip()[:50]
                
        print(f"[GrokAutomator] Creando etiqueta del proyecto: {project_label}")
        try:
            nueva_etiqueta_btn = page.locator('text="Nueva etiqueta"').first
            if await nueva_etiqueta_btn.is_visible(timeout=5000):
                await nueva_etiqueta_btn.click()
                await page.wait_for_timeout(1000)
                
                # Intentar escribir en el modal de nueva etiqueta
                # El placeholder es "Nombre de etiqueta"
                await page.keyboard.insert_text(project_label)
                await page.wait_for_timeout(500)
                
                crear_btn = page.locator('button:has-text("Crear"), div[role="button"]:has-text("Crear")').first
                await crear_btn.click()
                await page.wait_for_timeout(2000)
                
                # Entrar a la etiqueta recién creada
                my_label = page.locator(f'text="{project_label}"').first
                if await my_label.is_visible():
                    await my_label.click()
                    print(f"[GrokAutomator] [OK] Dentro de la etiqueta {project_label}.")
                    await page.wait_for_timeout(1000)
        except Exception as e:
            print(f"[GrokAutomator] ⚠️ No se pudo crear/entrar a la etiqueta: {e}. Se generará en 'Todas'.")
        
        # 2. Bucle principal en la MISMA página
        for idx, img_id in enumerate(expected_ids):
            output_video_path = os.path.join(output_folder, f"{img_id}.mp4")
            
            if os.path.exists(output_video_path):
                print(f"[GrokAutomator] Video para {img_id} ya existe. Saltando...")
                continue
                
            print(f"\n[GrokAutomator] [{idx+1}/{len(expected_ids)}] Esperando a que la imagen {img_id} sea generada por Google Flow...")
            
            # Bucle de escucha: espera hasta que aparezca la imagen en la carpeta
            wait_attempts = 0
            while not (os.path.exists(os.path.join(image_folder, f"{img_id}.png")) or os.path.exists(os.path.join(image_folder, f"{img_id}.jpg"))):
                if wait_attempts > 600: # 600 * 2s = 20 minutos max de espera
                    break
                await page.wait_for_timeout(2000)
                wait_attempts += 1
                
            filename = ""
            if os.path.exists(os.path.join(image_folder, f"{img_id}.png")):
                filename = f"{img_id}.png"
            elif os.path.exists(os.path.join(image_folder, f"{img_id}.jpg")):
                filename = f"{img_id}.jpg"
            else:
                print(f"[GrokAutomator] ⚠️ Tiempo de espera agotado para la imagen {img_id}. Saltando...")
                continue
                
            image_path = os.path.join(image_folder, filename)
            print(f"[GrokAutomator] ¡Imagen detectada! Animando {filename} en Grok...")
            
            # Click "Video"
            try:
                video_btn = page.locator('text="Video"').first
                if await video_btn.is_visible(timeout=3000):
                    await video_btn.click()
                    await page.wait_for_timeout(500)
            except:
                pass
                
            # Subir imagen
            print(f"  -> Subiendo imagen...")
            file_input = page.locator('input[type="file"]').first
            await file_input.set_input_files(image_path)
            await page.wait_for_timeout(2000)
            
            img_id = filename.split('.')[0]
            prompt_text = prompts_dict.get(img_id, "Animate this image beautifully") if prompts_dict else "Animate this image beautifully"
            
            print(f"  -> Escribiendo prompt...")
            await grok_input.click(force=True)
            await page.wait_for_timeout(500)
            await page.keyboard.press('Control+A')
            await page.keyboard.press('Backspace')
            await page.keyboard.insert_text(prompt_text)
            await page.wait_for_timeout(500)
            
            await page.keyboard.press('Enter')
            print(f"  -> Enviado. Esperando generación (aprox 30-45s)...")
            
            # Esperar a que el texto "Generando" aparezca y luego desaparezca
            generando_text = page.locator('text=/Generando/i').first
            try:
                # Darle unos segundos para que aparezca el cartel
                await generando_text.wait_for(state="visible", timeout=10000)
                print("  -> Grok está generando el video...")
                # Ahora esperar a que desaparezca
                await generando_text.wait_for(state="hidden", timeout=120000)
                print("  -> Generación terminada.")
            except:
                print("  -> No se detectó el cartel 'Generando', esperando 45s fijos por seguridad...")
                await page.wait_for_timeout(45000)
                
            await page.wait_for_timeout(3000) # Pausa extra para que aparezca la barra lateral
            
            download_success = False
            
            # Intento 1: Botón con aria-label
            try:
                descargar_btn = page.locator('button[aria-label*="ownload"], button[aria-label*="escargar"]').first
                if await descargar_btn.is_visible(timeout=2000):
                    print("  -> Botón de descarga encontrado (Aria). Descargando...")
                    async with page.expect_download(timeout=60000) as download_info:
                        await descargar_btn.click()
                    download = await download_info.value
                    await download.save_as(output_video_path)
                    download_success = True
            except:
                pass
                
            # Intento 2: Click derecho en el video
            if not download_success:
                try:
                    videos = page.locator('video')
                    if await videos.count() > 0:
                        vid = videos.last
                        await vid.click(button="right", force=True)
                        await page.wait_for_timeout(1000)
                        descargar_ctx = page.locator('text=/Descargar|Download/i').first
                        if await descargar_ctx.is_visible(timeout=2000):
                            print("  -> Opción de descarga encontrada (Click Derecho). Descargando...")
                            async with page.expect_download(timeout=60000) as download_info:
                                await descargar_ctx.click()
                            download = await download_info.value
                            await download.save_as(output_video_path)
                            download_success = True
                        # Clic fuera para cerrar menú contextual
                        await page.mouse.click(0, 0)
                except:
                    pass
            
            if download_success:
                print(f"  [OK] ✅ Guardado: {output_video_path}")
            else:
                print(f"  [ERROR] ❌ Falló la descarga de {filename}")
                
            # Cerrar la vista previa del video pulsando ESC o buscando el botón de cerrar
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(2000)
            
        print("\n[GrokAutomator] Proceso completado.")
        await browser.close()
