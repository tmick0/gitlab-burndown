import sys, gitlab, collections, datetime, dateutil.parser, pickle
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import scipy.interpolate as interpolate
import scipy.signal as signal

def dd_int():
    return collections.defaultdict(int)

def main(gitlab_url = None, gitlab_secret = None, project = None, since = None, output = None):

    if any([x is None for x in [gitlab_url, gitlab_secret, project]]):
        sys.stderr.write("usage: python3 %s <gitlab_url> <gitlab_secret> <project> [since-date-iso-fmt] [output-file]\n" % sys.argv[0])
        return 1
    
    all_points       = set()
    milestone_issues = collections.defaultdict(dd_int)
    milestone_names  = {}
    milestone_start  = {}
    most_recent      = None
    
    cache = None
    
    try:
        with open('issue_cache.pickle', 'rb') as f:
            cache = pickle.load(f)
        all_points = cache['all_points']
        milestone_issues = cache['milestone_issues']
        milestone_names = cache['milestone_names']
        milestone_start = cache['milestone_start']
        most_recent = max(all_points)
    except (IOError, EOFError):
        pass
    
    gl = gitlab.Gitlab(gitlab_url, gitlab_secret)
    proj = gl.projects.get(project)
    
    done = False
    page = 0
    while not done:
    
        issues = proj.issues.list(order_by='created_at', sort='desc', page=page, per_page=10)
        if len(issues) == 0:
            break
        page += 1
        
        print("fetched page %d" % page)
        
        for i in issues:
        
            # open time
            open_time = i.created_at
            
            # determine if we have caught up with the cache
            if most_recent is not None and open_time <= most_recent:
                done = True
                break
            
            # close time
            close_time = None
            for note in i.notes.list(order_by='created_at', sort='asc', all=True):
                if note.system and note.body.startswith('Status changed to closed'):
                    close_time = note.created_at
            
            # convert times to datetime obj
            open_time = dateutil.parser.parse(open_time)
            if close_time is not None:
                close_time = dateutil.parser.parse(close_time)
        
            # resolve milestone
            milestone = None, 'None'
            if i.milestone is not None:
                milestone = i.milestone.iid, i.milestone.title
            if not milestone[0] in milestone_names:
                milestone_names[milestone[0]] = milestone[1]
            if milestone[0] not in milestone_start or open_time < milestone_start[milestone[0]]:
                milestone_start[milestone[0]] = open_time
            
            # update deltas
            milestone_issues[milestone[0]][open_time]  += 1
            milestone_issues[milestone[0]][close_time] -= 1
            all_points |= set([open_time, close_time])
            
    # Remove 'None' point, it will break everything
    all_points -= set([None])
    
    # Save cache
    with open('issue_cache.pickle', 'wb') as f:
        cache = pickle.dump({
            'milestone_issues': milestone_issues,
            'all_points':       all_points,
            'milestone_names':  milestone_names,
            'milestone_start':  milestone_start
        }, f)
    
    # Build x and y
    x = sorted(all_points)
    y = [
        np.cumsum([   
            float(v[t]) for t in x
        ])
        for k, v in sorted(milestone_issues.items(), key=lambda x: milestone_start[x[0]])
    ]
    
    # Restrict domain
    if since is not None:
        since = dateutil.parser.parse(since)
        x = [t for t in x if t >= since]
        y = [
            yy[-len(x):]
            for yy in y
        ]
    
    # Filter empty series
    labels = [
        v
        for i, (k, v) in enumerate(sorted(
            milestone_names.items(), key=lambda p: milestone_start[p[0]]
        ))
        if any(k != 0 for k in y[i])
    ]
    y = [
        yy
        for yy in y
        if any(k != 0 for k in yy)
    ]

    # Smooth curve
    x_rel = [(t - x[0]).total_seconds() for t in x]
    xs_rel = np.linspace(x_rel[0], x_rel[-1], 250)
    ys = [
        signal.savgol_filter(
            interpolate.interp1d(x_rel, yy, kind='slinear')(xs_rel),
            51,
            4
        )
        for yy in y
    ]
    xs = [x[0] + datetime.timedelta(seconds=t) for t in xs_rel]
    
    # Generate color map
    cmap = cm.get_cmap('viridis')
    c = [cmap(int(cmap.N*i/len(ys))) for i in range(len(ys))]
    
    # Truncate names
    milestone_names = {
        i: (n if len(n) < 16 else n[:13]+"...")
        for i,n in milestone_names.items()
    }
    
    # Generate plot
    plt.figure(figsize=(10,4))
    plt.stackplot(xs, *ys, labels=labels, colors=c, baseline='zero', edgecolor='none')
    plt.legend(loc='upper center', shadow=True, ncol=3, fontsize='12')
    plt.ylim(0, plt.ylim()[1]*1.25)
    
    if output is None:
        plt.show()
    else:
        plt.savefig(output)
        
    return 0

if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
