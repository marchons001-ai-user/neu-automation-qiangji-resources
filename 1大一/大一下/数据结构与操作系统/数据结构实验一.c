#include <stdio.h>

void QuickSort(int* r,int l,int h){
	if(l>=h) return;
	int x=r[l];
	int i=l;
	int j=h;
	while(i<j){
		int key=0;
		while(1){
			if(x>r[j]){
				r[i]=r[j];
				break;
			}
			if(i>=j){
				key=1;
				break;
			}
			j--;
		}
		if(key==1) break;
		while(1){
			if(x<=r[i]){
				r[j]=r[i];
				break;
			}
			if(i>=j){
				key=1;
				break;
			}
			i++;
		}
		if(key==1) break;
	}
	r[i]=x;
	QuickSort(r,l,i-1);
	QuickSort(r,i+1,h);
}

void PutIn(int* r,int x,int low,int high){
	int max=high;
	int mid;
	while(low<=high){
		mid=(low+high)/2;
		if(r[mid]<=x&&x<=r[mid+1]){
			for(int i=max+1;i>=mid+2;i--){
				r[i]=r[i-1];
			}
			r[mid+1]=x;
			//printf("%d%d%d%d%d%d%d%d%d",r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7],r[8]);
			break;
		}
		if(r[mid]>x){
			high=mid-1;
		}
		if(r[mid+1]<x){
			low=mid+1;
		}
	}
	if(low>high){
		if(x<=r[0]){
			for(int i=max+1;i>=1;i--){
				r[i]=r[i-1];
			}
			r[0]=x;
		}
		if(x>=r[max]){
			r[max+1]=x;
		}
	}
}

int Delete(int* r,int y,int max){
	int m=0;
	for(int i=0;i<=max;i++){
		if(y==r[i]){
			int t=i;
			for(;i<=max;i++){
				r[i]=r[i+1];
			}
			i=t-1;
			m++;
		}
	}
	return m;
}

int main(){
	int i=0,r[100]={0},x=0,y=0;
	char c;
	printf("请输入一串数字：");
	do{
		scanf("%d",r+i);
		i++;
	}while((c=getchar())!='\n');
	int k=i;
	if(k>=100) printf("请输入少于100个数字。");
	QuickSort(r,0,k-1);
	for(i=0;i<k;i++) printf("%4d",r[i]);
	printf("\n请输入一个数字：");
	scanf("%d",&x);
	PutIn(r,x,0,k-1);
	for(i=0;i<k+1;i++) printf("%4d",r[i]);
	printf("\n请输入一个数字：");
	scanf("%d",&y);
	if(y<r[0]||y>r[k]) printf("ERROR");
	else{
		int a=Delete(r,y,k);
		if(a){
			for(i=0;i<k-a+1;i++) printf("%4d",r[i]);
		}
		else printf("ERROR");
	}
	return 0;
}