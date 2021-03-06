# coding=utf-8
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from .models import TeamPlayer, Teams
from .forms import TeamUpdateForm, TeamCreateForm
from accounts.models import User
from django.http import Http404
from django.db.models import  Q


def team_list_view(request):
    queryset_list = Teams.objects.all()
    query = request.GET.get("q")
    if query:
        queryset_list = queryset_list.filter(
                    Q(title__icontains=query)|
                    Q(teamplayer__user__nickname__icontains=query)
                    ).distinct()
    paginator = Paginator(queryset_list, 5) # Show 25 contacts per page
    page_request_var = "page"
    page = request.GET.get(page_request_var)
    try:
        queryset = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        queryset = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        queryset = paginator.page(paginator.num_pages)
    context = {
        "object_list": queryset,
        "page_request_var": page_request_var,
    }
    return render(request, 'teams/team_list.html', context)


def team_detail_view(request, team_id=None):
    teams = get_object_or_404(Teams, id=team_id)

    try:
        if request.user.is_authenticated():
            TeamPlayer.objects.get(team__title=teams.title, user=request.user, action=TeamPlayer.INTEAM )
            return redirect('teams:team_view', request.user.id)
        else:
            raise TeamPlayer.DoesNotExist
    except TeamPlayer.DoesNotExist:
        players = TeamPlayer.objects.filter(team__title=teams.title, user__is_inteam=True, action=TeamPlayer.INTEAM)
        context = {
                'team': teams,
                'players': players,
            }
        return render(request, 'teams/team_view.html', context)


def profile_team_view(request, user_id=None):
    current = False
    if request.user.is_authenticated():
        player = get_object_or_404(TeamPlayer, user__id=user_id)
        team = get_object_or_404(Teams, title=player.team.title)
        players = TeamPlayer.objects.filter(team__title=team.title, user__is_inteam=True, action=TeamPlayer.INTEAM)
        if request.user.pk == player.user.id:
            current = True
        context = {
            'team':team,
            'player':player,
            'players':players,
            'current':current
        }
        return render(request, 'teams/team_view.html', context)
    else:
        raise Http404


def team_update_view(request, user_id=None):
    if not request.user.is_captain:
        raise Http404
    player = get_object_or_404(TeamPlayer, user__id=user_id)
    form = TeamUpdateForm(request.POST or None, request.FILES or None, instance=player.team)
    players = TeamPlayer.objects.filter(team__title=player.team.title, action=TeamPlayer.INVITED)
    players_inteam = TeamPlayer.objects.filter(team__title=player.team.title, action=TeamPlayer.INTEAM)
    context = {
        'player': player,
        'form': form,
        'players':players,
        'players_inteam':players_inteam,
    }
    if form.is_valid():
        form.save()
        return redirect('teams:team_view', player.user.id)
    else:
        messages.warning(request, "Некорректные данные", extra_tags='info')
    return render(request, 'teams/team_edit.html', context)

@login_required
def invite_user_in_team(request, team_id=None):
    team = get_object_or_404(Teams, id=team_id)
    player = TeamPlayer.objects.create(team=team, user=request.user, action=TeamPlayer.INVITED)
    player.user.is_inteam = True
    player.user.save()
    return render(request, 'teams/invite_view.html', {})


def add_user_in_team(request, team_id=None):
    team = get_object_or_404(Teams, id=team_id)
    player = TeamPlayer.objects.filter(team__title=team.title, action=TeamPlayer.INVITED).first()
    player.action = TeamPlayer.INTEAM
    player.save()
    return redirect("teams:team_update_view", request.user.id)


def reject_user_from_team(request, team_id=None):
    team = get_object_or_404(Teams, id=team_id)
    player = TeamPlayer.objects.filter(team__title=team.title, action=TeamPlayer.INVITED).first()
    player.user.is_inteam = False
    player.user.is_captain = False
    player.user.save()
    player.delete()
    if request.user.is_captain:
        return redirect("teams:team_update_view", request.user.id)
    else:
        return redirect("teams:list_view")


def delete_user_from_team(request, user_id=None):
    user = get_object_or_404(User, id=user_id)
    player = TeamPlayer.objects.get(user=user, action=TeamPlayer.INTEAM)
    player.user.is_inteam = False
    player.user.is_captain = False
    player.user.save()
    player.delete()
    if request.user.is_captain:
        return redirect("teams:team_update_view", request.user.id)
    else:
        return redirect("teams:list_view")


def team_create_view(request, user_id=None):
    user = get_object_or_404(User, id=user_id)
    form = TeamCreateForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        user.is_inteam = True
        user.is_captain = True
        user.save()
        logo = form.cleaned_data['logo']
        title = form.cleaned_data['title']
        team = Teams.objects.create(title=title, logo=logo, captain_user=user)
        TeamPlayer.objects.create(team=team, user = user, action = TeamPlayer.INTEAM)
        return render(request, 'teams/create_success_view.html', {})
    else:
        messages.warning(request, "Некорректные данные", extra_tags='info')
        return render(request, 'teams/team_edit.html', {'form':form})


def team_delete_view(request, user_id=None):
    if not request.user.is_captain:
        raise Http404
    player = get_object_or_404(TeamPlayer, user__id=user_id)
    player.user.is_inteam = False
    player.user.is_captain = False
    player.user.save()
    team = get_object_or_404(Teams, title=player.team.title)
    player.delete()
    team.delete()
    return render(request, 'teams/team_delete_view.html', {})
