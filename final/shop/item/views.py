from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib.auth.models import User

from .forms import NewItemForm, EditItemForm
from .models import Item, Category
from django.contrib.auth.decorators import login_required
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .serializers import ItemSerializer, CategorySerializer
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework import status
from .tasks import send_new_item_notification


# Create your views here.
@api_view(['GET'])
def items(request):
    query = request.GET.get('query', '')
    category_id = request.GET.get('category', 0)
    # categories = Category.objects.all()
    items = Item.objects.filter(is_sold=False)

    if category_id:
        items = items.filter(category_id=category_id)

    if query:
        items = items.filter(Q(name__icontains=query) | Q(description__icontains=query))

    return Response(ItemSerializer(items, many=True).data, status=200, template_name='item/items.html')


@api_view(['GET'])
def detail(request, pk):
    item = get_object_or_404(Item, pk=pk)
    related_items = Item.objects.filter(category=item.category, is_sold=False).exclude(pk=pk)[0:3]
    return Response(ItemSerializer(item).data, status=200, template_name='item/detail.html')


@login_required
def new(request):
    if request.method == 'POST':
        form = NewItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.created_by = request.user
            item.save()
            for user in User.objects.all():
                send_new_item_notification.send(user.id, item.name)
            return redirect('item:detail', pk=item.id)
    else:
        form = NewItemForm()

    return render(request, 'item/form.html', {
        'form': form,
        'title': 'New Item',
    })

@login_required
def edit(request, pk):
    item = get_object_or_404(Item, pk=pk, created_by=request.user)

    if request.method == 'POST':
        form = EditItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()

            return redirect('item:detail', pk=item.id)
    else:
        form = EditItemForm(instance=item)

    return render(request, 'item/form.html', {
        'form': form,
        'title': 'Edit Item',
    })

@login_required
def delete(request, pk):
    item = get_object_or_404(Item, pk=pk, created_by=request.user)
    item.delete()

    return redirect('dashboard:index')


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def mark_as_sold(self, request, pk=None):
        item = self.get_object()
        item.is_sold = True
        item.save()
        return Response({'status': 'item marked as sold'})

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_items(self, request):
        items = Item.objects.filter(created_by=request.user)
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)


# @api_view(['GET'])
# def run_task(request):
#     send_new_item_notification.send(request.user.id, "Sample Item")
#     return Response({'status': 'Task is running'})