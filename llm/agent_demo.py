# %%
from agent import analyze_news
from IPython.display import Markdown, display

def display_result(result):
    display(Markdown(f"# {result['ticker']} Analysis"))
    display(Markdown("## Summary"))
    display(Markdown(result['summary']))
    display(Markdown("## Analysis"))
    display(Markdown(result['analysis']))

# %%
raw_result = analyze_news("NVDA")

# %%
result = raw_result['structured_response'].model_dump()
display_result(result)


# %%
