import json
from playwright.async_api import async_playwright
import click
import asyncio


async def get_info(page, link):
    await page.goto(link, timeout=0)
    await page.wait_for_selector('section.warning')

    content = await page.evaluate('''
        () => {
            const element = document.querySelector(
                'div.item_detail:has(p):has(img[src="https://www.portaljob-madagascar.com/application/resources/images/view/profil.jpg"])'
            );

            return element?.textContent?.replaceAll('\\n\\n                \\n                ', '').replaceAll('            ', '').replaceAll('\\n\\n\\n', '');
        }
    ''')

    return content


async def get_current_page(filename):
    try:
        with open(filename, 'r') as file:
            data = json.load(file)
            list_data = data['list']

            return len(list_data) + 1
    except FileNotFoundError:
        return 1


async def write_to_json(filename, list_data, contents):
    try:
        with open(filename, 'r') as file:
            data = json.load(file)

        data['list'].extend(list_data)
        data['contents'].extend(contents)
    except FileNotFoundError:
        data = {'list': list_data, 'contents': contents}

    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)


async def main(number_pages):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, timeout=0)
        context = await browser.new_context()

        FILE = 'result.json'

        currentPage = await get_current_page(FILE)
        MAX = currentPage + number_pages

        base_url = 'https://www.portaljob-madagascar.com/emploi/liste/secteur/informatique-web/page/'

        list_data = []
        contents = []

        try:
            while currentPage < MAX:
                page = await context.new_page()
                url = f'{base_url}{currentPage}'

                print(currentPage)

                try:
                    await page.goto(url, timeout=0)
                    await page.wait_for_selector('div.pagination')

                    articles_data = await page.evaluate('''
                        () => {
                            const articles = Array.from(document.querySelectorAll('article[class="item_annonce"]'));

                            return articles.map(article => {
                                return {
                                    date: article.querySelector('aside.date_annonce > .date')?.textContent?.replaceAll('\\n', ' '),
                                    title: article.querySelector('aside.contenu_annonce > h3 > a')?.textContent || '',
                                    link: (article.querySelector('aside.contenu_annonce > h3 > a')?.href) || '',
                                    company: article.querySelector('aside.contenu_annonce > h4')?.textContent || ''
                                }
                            });
                        }
                    ''')

                    for i in range(len(articles_data)):
                        content = await get_info(page, articles_data[i]['link'])
                        contents.append({'link': articles_data[i]['link'], 'content': content})

                    list_data.append(articles_data)

                except Exception as e:
                    print(f"An error occurred while scraping page {currentPage}: {str(e)}")

                await page.close()

                currentPage += 1

            await write_to_json(FILE, list_data, contents)
        finally:
            await context.close()
            
            await browser.close()


@click.command()
@click.version_option("0.1.0", prog_name="PortalJob Web Scraper")
@click.option('-n', '--number-pages', type=click.INT, required=True, help='Number of pages to scrape. Beware of `out of bound number of pages`.')
def cli(number_pages):
    asyncio.get_event_loop().run_until_complete(main(number_pages))


if __name__ == '__main__':
    cli()
