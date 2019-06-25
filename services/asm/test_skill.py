import aiohttp
import asyncio


async def main():
    dialog = ["quiero cotizacion seguro", "31012"]
    skills = ["abot"]
    user = "test"
    channel = "slack"
    debug = True

    for iteration in dialog:
        best_skill = None
        best_skill_data = None
        for skill in skills:
            async with aiohttp.ClientSession() as session:
                async with session.post('http://localhost:8080/api/v1/skill/parse',
                                        json={'text': iteration}) as resp:
                    result = await resp.json()
                    if best_skill is None or result['intent']['confidence'] > best_skill['intent']['confidence']:
                        best_skill = skill
                        best_skill_data = result

        best_skill_data['user'] = user
        best_skill_data['channel'] = channel

        if debug:
            print(best_skill_data)
        async with aiohttp.ClientSession() as session:
            async with session.post('http://localhost:8080/api/v1/skill/next_step',
                                    json=best_skill_data) as resp:
                result = await resp.json()
                print(result['text'])

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
