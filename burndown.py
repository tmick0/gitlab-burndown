import sys, gitlab, intervaltree, collections, datetime

def main(gitlab_url = None, gitlab_secret = None, project = None):

    if any([x is None for x in [gitlab_url, gitlab_secret, project]]):
        sys.stderr.write("usage: python3 %s <gitlab_url> <gitlab_secret> <project>\n" % sys.argv[0])
        return 1
    
    milestone_issues = collections.defaultdict(intervaltree.IntervalTree)
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
        open_time = datetime.datetime.strptime(open_time, "%Y-%m-%dT%H:%M:%SZ")
        if close_time is not None:
            close_time = datetime.datetime.strptime(close_time, "%Y-%m-%dT%H:%M:%SZ")
        
        # add to tree    
        milestone_issues[milestone[0]].addi(open_time, close_time, None)
        
    return 0

if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
