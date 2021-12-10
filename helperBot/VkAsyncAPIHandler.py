

async def vk_polling(vkuser: VkUser):
    log.warning('Starting polling for: id ' + str(vkuser.pk))
    while True:
        try:
            session = VkSession(access_token=vkuser.token, driver=await get_driver(vkuser.token))
            api = API(session)
            lp = LongPoll(session, mode=10, version=4)
            while VkUser.objects.filter(token=vkuser.token, is_polling=True).exists():
                data = await lp.wait()
                log.warning(f'Longpoll id {vkuser.pk}: ' + str(data))
                if data['updates']:
                    for update in data['updates']:
                        await process_longpoll_event(api, update)
            break
        except VkLongPollError:
            log.error('Longpoll error! {}'.format(vkuser.pk))
            await asyncio.sleep(5)
        except VkAuthError:
            log.error('Auth Error! {}'.format(vkuser.pk))
            vkuser.is_polling = False
            vkuser.save()
            break
        except TimeoutError:
            log.warning('Polling timeout')
            await asyncio.sleep(5)
        except CancelledError:
            log.warning('Stopped polling for id: ' + str(vkuser.pk))
            break
        except aiohttp.client_exceptions.ServerDisconnectedError:
            log.warning('Longpoll server disconnected id: ' + str(vkuser.pk))
        except VkAPIError:
            # Invalid/Inaccessible token
            pass
        except Exception:
            log.exception(msg='Error in longpolling', exc_info=True)
            await asyncio.sleep(5)


def vk_polling_tasks():
    tasks = [{'token': vkuser.token, 'task': asyncio.ensure_future(vk_polling(vkuser))} for vkuser in
             VkUser.objects.filter(token__isnull=False, is_polling=True)]
    log.warning('Starting Vk polling')
    return tasks