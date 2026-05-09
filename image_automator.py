import os
import time
import asyncio
from playwright.async_api import async_playwright

async def generate_batch_images_flow(prompts, output_folder, ref_image_path=None):
    """
    Automates Google Flow (ImageFX) using Playwright.
    """
    user_data_dir = os.path.join(os.getcwd(), 'playwright_data_google')
    os.makedirs(user_data_dir, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)

    print(f"[ImageAutomator] Iniciando Playwright para Google Flow...")
    
    async with async_playwright() as p:
        # Usamos chrome igual que con Fish Audio para evitar bloqueos
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            channel="chrome", 
            viewport={'width': 1280, 'height': 800},
            ignore_default_args=["--enable-automation"],
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        print(f"[ImageAutomator] Navegando a Google Flow...")
        await page.goto('https://labs.google/fx/es/tools/flow')
        
        # Buscamos la caja de texto principal usando el data-slate-editor que pasaste en la captura
        textbox = page.locator('div[data-slate-editor="true"]').first
        
        try:
            # Esperamos a que el textbox sea visible (significa que está logueado y la página cargó)
            await textbox.wait_for(state="visible", timeout=10000)
        except:
            print("\n=======================================================")
            print("[INFO] PARECE QUE NECESITAS INICIAR SESIÓN EN GOOGLE")
            print("=======================================================")
            print("[ATENCION] Google requiere que inicies sesión en tu cuenta para usar Flow.")
            print("Esperando hasta 5 minutos a que inicies sesión y cargue la página principal de Flow...")
            await textbox.wait_for(state="visible", timeout=300000)
            print("[OK] Sesión detectada en Google Flow. Continuamos.\n")
            
        # Si hay imagen de referencia, la subimos
        if ref_image_path and os.path.exists(ref_image_path):
            print("[ImageAutomator] Subiendo imagen de referencia...")
            try:
                # La mayoría de las webs modernas tienen un input type="file" oculto para el upload
                file_input = page.locator('input[type="file"]').first
                await file_input.wait_for(state="attached", timeout=5000)
                await file_input.set_input_files(ref_image_path)
                print("[ImageAutomator] [OK] Imagen de referencia enviada. Esperando 15 segundos a que cargue completamente en Flow...")
                # Pausa larga porque Flow tarda en procesar las imágenes subidas
                await page.wait_for_timeout(15000)
            except Exception as e:
                print(f"[ImageAutomator] [WARNING] No se pudo subir la imagen de referencia automáticamente: {e}")
                print("[ImageAutomator] Por favor, súbela manualmente ahora. Tienes 15 segundos...")
                await page.wait_for_timeout(15000)
        
        print(f"[ImageAutomator] Procesando {len(prompts)} prompts...")
        
        for index, prompt_data in enumerate(prompts):
            prompt_id = prompt_data['id']
            text = prompt_data['text']
            
            output_path = os.path.join(output_folder, f"{prompt_id}.png")
            if os.path.exists(output_path):
                print(f"[ImageAutomator] Imagen {prompt_id} ya existe. Saltando...")
                continue
                
            print(f"[ImageAutomator] Generando imagen para prompt {prompt_id}...")
            
            # Limpiar la caja de texto
            print(f"[ImageAutomator] Limpiando caja de texto...")
            await textbox.click(force=True)
            await page.wait_for_timeout(500)
            await page.keyboard.press('Control+A')
            await page.keyboard.press('Backspace')
            await page.wait_for_timeout(500)
            
            # Escribir el nuevo prompt
            print(f"[ImageAutomator] Escribiendo prompt...")
            
            # Añadir referencia de imagen si existe
            if ref_image_path and os.path.exists(ref_image_path):
                # Usar .type en lugar de .insert_text es CRUCIAL en Slate.js para disparar el menú
                await page.keyboard.type("@", delay=150)
                await page.wait_for_timeout(2000) # Esperamos que abra el menú
                
                # Escribimos el nombre del archivo lentamente para que lo filtre
                await page.keyboard.type("ref_image", delay=100)
                await page.wait_for_timeout(2000) # Esperamos que filtre
                
                # Presionamos Enter para seleccionar la imagen resaltada en el menú
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(1000)
                
            # Escribir el prompt principal de una vez (esto puede ser rápido)
            await page.keyboard.insert_text(text)
            await page.wait_for_timeout(1000)
            
            # Guardar los SRC de las imágenes actuales y marcarlas con una clase en el DOM.
            await page.evaluate('''() => {
                window.oldImageSrcs = Array.from(document.querySelectorAll('img')).map(img => img.src).filter(src => src);
                document.querySelectorAll('img').forEach(img => {
                    img.classList.add('my-old-image-mark');
                });
            }''')
            
            # Marcar los errores viejos (políticas o genéricos) para no volver a detectarlos
            old_errors = page.locator('text=/infringir|vaya, se ha producido un error/i')
            for i in range(await old_errors.count()):
                try:
                    await old_errors.nth(i).evaluate('node => node.classList.add("my-old-error-mark")')
                except:
                    pass
                
            # Enviar el prompt
            print("[ImageAutomator] Enviando petición a Google Flow...")
            await page.keyboard.press('Control+Enter')
            await page.wait_for_timeout(500)
            
            try:
                await page.keyboard.press('Enter')
            except:
                pass
            
            print("[ImageAutomator] Esperando a que se generen las imágenes (tiempo dinámico hasta 300s)...")
            
            generation_done = False
            policy_error_triggered = False
            
            for attempt in range(150): # 150 * 2s = 300s
                local_errors = page.locator('text=/infringir|vaya, se ha producido un error/i')
                local_errors_count = 0
                for i in range(await local_errors.count()):
                    try:
                        if await local_errors.nth(i).is_visible():
                            has_mark = await local_errors.nth(i).evaluate('node => node.classList.contains("my-old-error-mark")')
                            if not has_mark:
                                local_errors_count += 1
                    except:
                        pass
                    
                # Buscar solo imágenes que sean verdaderamente nuevas
                new_images_count = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('img')).filter(img => {
                        if (img.classList.contains('my-old-image-mark')) return false;
                        if (window.oldImageSrcs && img.src && window.oldImageSrcs.includes(img.src)) return false;
                        const rect = img.getBoundingClientRect();
                        return rect.width >= 100 && rect.height >= 100;
                    }).length;
                }''')
                        
                if new_images_count + local_errors_count >= 2:
                    if new_images_count > 0:
                        print(f"[ImageAutomator] ¡{new_images_count} nuevas imágenes detectadas en {attempt*2} segundos!")
                        await page.wait_for_timeout(4000) # Dar tiempo a que el renderizado de Flow se asiente
                        generation_done = True
                        break
                    else:
                        print(f"[ImageAutomator] [ERROR] Todas las imágenes del prompt {prompt_id} fallaron (políticas o genérico).")
                        policy_error_triggered = True 
                        break
                    
                await page.wait_for_timeout(2000)
                
            if policy_error_triggered:
                print(f"[ImageAutomator] [INFO] Saltando descarga para el prompt {prompt_id} debido a error de políticas.")
                await page.wait_for_timeout(2000)
                continue 
            
            print("[ImageAutomator] Buscando y descargando la primera imagen generada válida (vía click derecho)...")
            
            images = page.locator('img')
            download_success = False
            
            for i in range(min(20, await images.count())):
                try:
                    img = images.nth(i)
                    
                    # Verificar si es vieja usando evaluate y la propiedad src
                    is_old = await img.evaluate('''(node) => {
                        if (node.classList.contains('my-old-image-mark')) return true;
                        if (window.oldImageSrcs && node.src && window.oldImageSrcs.includes(node.src)) return true;
                        return false;
                    }''')
                    
                    if is_old:
                        continue
                        
                    # Ignorar imágenes pequeñas
                    box = await img.bounding_box()
                    if not box or box['width'] < 100 or box['height'] < 100:
                        continue
                        
                    # Hacemos click derecho
                    await img.click(button="right", force=True)
                    await page.wait_for_timeout(1000) # Esperamos a que abra el menú
                    
                    # Ver si aparece la opción "Descargar" o "Download"
                    descargar_btn = page.locator('text=/Descargar|Download/i').first
                    if await descargar_btn.is_visible():
                        # Hacemos hover para que se abra el submenú de 1K
                        await descargar_btn.hover()
                        await page.wait_for_timeout(1000)
                        
                        # Buscar la opción "1K"
                        btn_1k = page.locator('text="1K"').first
                        if await btn_1k.is_visible():
                            print(f"[ImageAutomator] Opción 1K encontrada para la imagen {prompt_id}. Descargando...")
                            async with page.expect_download(timeout=60000) as download_info:
                                await btn_1k.click()
                            download = await download_info.value
                            await download.save_as(output_path)
                            print(f"[ImageAutomator] [OK] Imagen {prompt_id} guardada con éxito en {output_path}.")
                            download_success = True
                            
                            # Hacer click fuera para cerrar cualquier menú flotante
                            await page.mouse.click(0, 0)
                            break
                        else:
                            await page.mouse.click(0, 0)
                    else:
                        await page.mouse.click(0, 0)
                except Exception as e:
                    await page.mouse.click(0, 0)
                    continue
            
            if not download_success:
                print(f"[ImageAutomator] [WARNING] No se logró descargar automáticamente la imagen {prompt_id}.")
                print("[ImageAutomator] Tienes 15 segundos para descargarla manualmente.")
                await page.wait_for_timeout(15000)
            
            # Wait a bit before next prompt
            await page.wait_for_timeout(2000)
            
        print("[ImageAutomator] ¡Proceso de imágenes completado!")
        await browser.close()
