import sys, gitlab, collections, datetime, dateutil.parser
import numpy as np
import matplotlib.pyplot as plt

def main(gitlab_url = None, gitlab_secret = None, project = None):

    if any([x is None for x in [gitlab_url, gitlab_secret, project]]):
        sys.stderr.write("usage: python3 %s <gitlab_url> <gitlab_secret> <project>\n" % sys.argv[0])
        return 1
    
    all_points       = set()
    milestone_issues = collections.defaultdict(lambda: collections.defaultdict(lambda: 0))
    milestone_names  = {}
    
    gl = gitlab.Gitlab(gitlab_url, gitlab_secret)
    proj = gl.projects.get(project)

    for i in proj.issues.list(order_by='created_at', sort='desc', all=True):
    
        # resolve milestone
        milestone = None, 'None'
        if i.milestone is not None:
            milestone = i.milestone.iid, i.milestone.title
        if not milestone[0] in milestone_names:
            milestone_names[milestone[0]] = milestone[1]
            
        # open time
        open_time = i.created_at
        
        # close time
        close_time = None
        for note in i.notes.list(order_by='created_at', sort='asc', all=True):
            if note.system and note.body.startswith('Status changed to closed'):
                close_time = note.created_at
        
        # convert times to datetime obj
        open_time = dateutil.parser.parse(open_time)
        if close_time is not None:
            close_time = dateutil.parser.parse(close_time)
        
        # update deltas
        milestone_issues[milestone[0]][open_time]  += 1
        milestone_issues[milestone[0]][close_time] -= 1
        all_points |= set([open_time, close_time])
        
    all_points -= set([None])
        
    x = sorted(all_points)
    y = [
        np.cumsum([   
            v[t] for t in x
        ])
        for k, v in sorted(milestone_issues.items(), key=lambda x: milestone_names[x[0]])
    ]
    
    plt.stackplot(x, *y, labels=sorted(milestone_names.values()))
    plt.legend()
    plt.show()
        
    return 0

if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
