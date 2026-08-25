import json

def patch_nb5():
    path = 'e:/Capstone/NoteBooks/nb5_model_training_lifestyle_FIXED.ipynb'
    with open(path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = ''.join(cell['source'])
            if 'XGBClassifier(' in source and 'monotone_constraints' not in source:
                new_source = source.replace(
                    "tree_method='hist', eval_metric='logloss',",
                    "tree_method='hist', eval_metric='logloss',\n                      monotone_constraints=(1, 0, 1, 1, 1, 1, -1, 1, 0, 0, 0, 0, 0, 0),"
                )
                
                # Split back to list of strings with newlines
                lines = new_source.split('\n')
                cell['source'] = [line + '\n' for line in lines[:-1]] + [lines[-1]] if lines[-1] else [line + '\n' for line in lines]
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(nb, f)
    print("NB5 patched.")

def patch_nb6():
    path = 'e:/Capstone/NoteBooks/nb6_model_training_clinical.ipynb'
    with open(path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = ''.join(cell['source'])
            if 'XGBClassifier(' in source and 'monotone_constraints' not in source:
                new_source = source.replace(
                    "eval_metric='logloss',",
                    "eval_metric='logloss',\n            monotone_constraints=(1, 0, 1, 1, 1, -1, 1, 0, 0, 0),"
                )
                
                lines = new_source.split('\n')
                cell['source'] = [line + '\n' for line in lines[:-1]] + [lines[-1]] if lines[-1] else [line + '\n' for line in lines]
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(nb, f)
    print("NB6 patched.")

patch_nb5()
patch_nb6()
