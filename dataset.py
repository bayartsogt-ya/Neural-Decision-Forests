import torch
from torch.utils.data import Dataset
import os
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from iterstrat.ml_stratifiers import MultilabelStratifiedKFold

class MoA(Dataset):
    def __init__(self,root,train=True, n_folds=5, fold=0):
        super(MoA,self).__init__()
        self.root = os.path.expanduser(root)
        self.train = train
        self.n_folds = n_folds
        self.fold = fold
        self.X, self.y = self.load_data()

    def __getitem__(self, index):
        return (self.X[index],self.y[index])

    def __len__(self):
        return len(self.X)

    def load_data(self):
        df_train_features          = pd.read_csv(f'{self.root}/train_features.csv')
        df_train_targets_scored    = pd.read_csv(f'{self.root}/train_targets_scored.csv')
        # df_train_targets_nonscored = pd.read_csv(f'{self.root}/train_targets_nonscored.csv')
        df_train_drug              = pd.read_csv(f'{self.root}/train_drug.csv')
        # df_test_features           = pd.read_csv(f'{self.root}/test_features.csv')
        # df_sample_submission       = pd.read_csv(f'{self.root}/sample_submission.csv')

        col_genes   = [col for col in df_train_features.columns.to_list() if col[:2] == "g-"]
        col_cells   = [col for col in df_train_features.columns.to_list() if col[:2] == "c-"]
        col_cats    = ["cp_time", "cp_dose"]

        col_targets = df_train_targets_scored.columns.to_list()[1:]


        df_train = df_train_features.merge(df_train_targets_scored, how="left", on="sig_id")
        df_train = df_train.merge(df_train_drug, on="sig_id", how="left")
        df_train = df_train.dropna()

        ### FOLD 
        seed = 42

        vc = df_train.drug_id.value_counts()
        vc1 = vc.loc[vc<=18].index.sort_values()
        vc2 = vc.loc[vc>18].index.sort_values()

        # STRATIFY DRUGS 18X OR LESS
        dct1 = {}; dct2 = {}
        skf = MultilabelStratifiedKFold(n_splits=self.n_folds, shuffle=True, random_state=seed)
        tmp = df_train.groupby('drug_id')[col_targets].mean().loc[vc1]
        for fold,(idxT,idxV) in enumerate( skf.split(tmp,tmp[col_targets])):
            dd = {k:fold for k in tmp.index[idxV].values}
            dct1.update(dd)

        # STRATIFY DRUGS MORE THAN 18X
        skf = MultilabelStratifiedKFold(n_splits=self.n_folds, shuffle=True, random_state=seed)
        tmp = df_train.loc[df_train.drug_id.isin(vc2)].reset_index(drop=True)
        for fold,(idxT,idxV) in enumerate( skf.split(tmp,tmp[col_targets])):
            dd = {k:fold for k in tmp.sig_id[idxV].values}
            dct2.update(dd)

        # ASSIGN FOLDS
        df_train['fold'] = df_train.drug_id.map(dct1)
        df_train.loc[df_train.fold.isna(),'fold'] =\
            df_train.loc[df_train.fold.isna(),'sig_id'].map(dct2)
        df_train.fold = df_train.fold.astype('int8')

        # EXCLUDE CONTROL GROUP
        df_train = df_train.loc[df_train.cp_type=="trt_cp"]
        df_train = df_train.reset_index(drop=True)

        # convert categorical data
        df_train.loc[:, 'cp_dose'] = df_train.loc[:, 'cp_dose'].map({'D1': 0, 'D2': 1})

        # getting all input columns
        col_input = col_cats + col_cells + col_genes

        if self.train:
            train_df = df_train[df_train['fold'] != self.fold].reset_index(drop=True)
            X, y  = train_df[col_input].values, train_df[col_targets].values


        else:
            valid_df = df_train[df_train['fold'] == self.fold].reset_index(drop=True)
            X, y =  valid_df[col_input].values, valid_df[col_targets].values
        

        X = torch.from_numpy(X).type(torch.FloatTensor)
        y = torch.from_numpy(y).type(torch.FloatTensor)
        return X,y


class UCIAdult(Dataset):
    def __init__(self,root,train=True):
        super(UCIAdult,self).__init__()
        self.root = os.path.expanduser(root)
        self.train = train
        # 65, Private, 198766, Masters, 14, Married-civ-spouse, Sales, Husband, White, Male, 20051, 0, 40, United-States, >50K
        self.fields = [{'type':'num'},
                       {'type':'cate','choices':['unk','Private', 'Self-emp-not-inc', 'Self-emp-inc', 'Federal-gov', 'Local-gov', 'State-gov', 'Without-pay', 'Never-worked']},
                       {'type': 'num'},
                       {'type': 'cate', 'choices': ['unk','Bachelors', 'Some-college', '11th', 'HS-grad', 'Prof-school', 'Assoc-acdm', 'Assoc-voc', '9th', '7th-8th', '12th', 'Masters', '1st-4th', '10th', 'Doctorate', '5th-6th', 'Preschool']},
                       {'type': 'num'},
                       {'type': 'cate', 'choices': ['unk','Married-civ-spouse', 'Divorced', 'Never-married', 'Separated', 'Widowed', 'Married-spouse-absent', 'Married-AF-spouse' ]},
                       {'type': 'cate', 'choices': ['unk','Tech-support', 'Craft-repair', 'Other-service', 'Sales', 'Exec-managerial', 'Prof-specialty', 'Handlers-cleaners', 'Machine-op-inspct', 'Adm-clerical', 'Farming-fishing', 'Transport-moving', 'Priv-house-serv', 'Protective-serv', 'Armed-Forces' ]},
                       {'type': 'cate', 'choices': ['unk', 'Wife', 'Own-child', 'Husband', 'Not-in-family', 'Other-relative', 'Unmarried']},
                       {'type': 'cate', 'choices': ['unk', 'White', 'Asian-Pac-Islander', 'Amer-Indian-Eskimo', 'Other', 'Black']},
                       {'type': 'cate', 'choices': ['unk', 'Female', 'Male']},
                       {'type': 'num'},
                       {'type': 'num'},
                       {'type': 'num'},
                       {'type': 'cate', 'choices': ['unk', 'United-States', 'Cambodia', 'England', 'Puerto-Rico', 'Canada', 'Germany', 'Outlying-US(Guam-USVI-etc)', 'India', 'Japan', 'Greece', 'South', 'China', 'Cuba', 'Iran', 'Honduras', 'Philippines', 'Italy', 'Poland', 'Jamaica', 'Vietnam', 'Mexico', 'Portugal', 'Ireland', 'France', 'Dominican-Republic', 'Laos', 'Ecuador', 'Taiwan', 'Haiti', 'Columbia', 'Hungary', 'Guatemala', 'Nicaragua', 'Scotland', 'Thailand', 'Yugoslavia', 'El-Salvador', 'Trinadad&Tobago', 'Peru', 'Hong', 'Holand-Netherlands']},
                       ]

        for field in self.fields:
            if field['type'] == 'cate':
                field['w2i'] = dict([(w,i) for i,w in enumerate(field['choices'])])

        self.X, self.y = self.load_data(root,train)


    def __getitem__(self, index):
        return (self.X[index],self.y[index])

    def __len__(self):
        return len(self.X)


    def load_data(self,root,train):
        if train:
            data_path = os.path.join(root,"adult.data")
        else:
            data_path = os.path.join(root, "adult.test")

        with open(data_path) as f:
            rows = [ [ fv.strip() for fv in row.strip().split(",")] for row in f.readlines() if len(row.strip()) > 0 and not row.startswith("|")]
        n_datas = len(rows)
        X_dim = np.sum([ 1 if field['type']=='num' else len(field['choices']) for field in self.fields])
        X = np.zeros((n_datas, X_dim), dtype=np.float32)
        y = np.zeros(n_datas, dtype=np.int32)
        for i, row in enumerate(rows):
            assert len(row) == 15
            foffset = 0
            for j in range(14):
                if self.fields[j]['type'] == 'num':
                    fdim=1
                    X[i, foffset] = float(row[j])
                else:
                    fdim = len(self.fields[j]['choices'])
                    hit = self.fields[j]['w2i'].get(row[j],0)
                    X[i, foffset+hit] = 1
                foffset += fdim

            y[i] = 0 if row[-1].strip().startswith("<=50K") else 1

        X_min = np.array([[17.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 12285.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
        X_max = np.array([[90.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1484705.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 16.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0, 99999.0, 4356.0, 99.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]])
        X = (X - X_min) / np.clip((X_max - X_min), a_min=1e-6, a_max=None)

        #print([float(i) for i in np.min(X, axis=0)])
        #print([float(i) for i in np.max(X, axis=0)])


        X = torch.from_numpy(X).type(torch.FloatTensor)
        y = torch.from_numpy(y).type(torch.IntTensor)
        return X, y


class UCILetter(Dataset):
    def __init__(self,root,train=True):
        super(UCILetter,self).__init__()
        self.root = os.path.expanduser(root)
        self.train = train
        self.X, self.y = self.load_data(root,train)


    def __getitem__(self, index):
        return (self.X[index],self.y[index])

    def __len__(self):
        return len(self.X)

    def load_data(self,root,train):
        data_path = os.path.join(root, "letter-recognition.data")
        with open(data_path) as f:
            rows = [[ item.strip() for item in row.strip().split(',')] for row in f.readlines()]
        if train:
            rows = rows[:16000]
        else:
            rows = rows[16000:]

        n_datas = len(rows)
        X = np.zeros((n_datas, 16), dtype=np.float32)
        y = np.zeros(n_datas, dtype=np.int32)
        for i, row in enumerate(rows):
            X[i, :] = list(map(float, row[1:]))
            y[i] = ord(row[0]) - ord('A')

        X = torch.from_numpy(X).type(torch.FloatTensor)
        y = torch.from_numpy(y).type(torch.IntTensor)
        return X,y


class UCIYeast(Dataset):
    def __init__(self,root,train=True):
        super(UCIYeast,self).__init__()
        self.root = os.path.expanduser(root)
        self.train = train
        self.labels = ['CYT','NUC','MIT','ME3','ME2','ME1','EXC','VAC','POX','ERL']
        self.labels2idx = dict([ (label,i) for i,label in enumerate(self.labels)])

        self.X, self.y = self.load_data(root,train)


    def __getitem__(self, index):
        return (self.X[index],self.y[index])

    def __len__(self):
        return len(self.X)


    def _load_data(self,data_path):
        with open(data_path) as f:
            rows = [ row.strip().split() for row in f.readlines()]
        n_datas = len(rows)
        X = np.zeros((n_datas, 8), dtype=np.float32)
        y = np.zeros(n_datas, dtype=np.int32)
        for i, row in enumerate(rows):
            X[i, :] = list(map(float, row[1:-1]))
            y[i] = self.labels2idx[row[-1]]
        return X,y

    def _write_data(self, X, y, data_path):
        with open(data_path,'w') as f:
            for X_, y_ in zip(X,y):
                feat = ' '.join([str(x) for x in X_])
                f.write('placeholder %s %s\n'%(feat,self.labels[y_]))

    def load_data(self,root,train):
        if not os.path.exists(os.path.join(root, "yeast.train")) or \
            not os.path.exists(os.path.join(root, "yeast.test")):
            data_path = os.path.join(root, "yeast.data")
            X,y = self._load_data(data_path)
            n_datas = len(y)
            train_idx, test_idx = train_test_split(range(n_datas), random_state=0, train_size=0.7, stratify=y)
            self._write_data(X[train_idx],y[train_idx],os.path.join(root, "yeast.train"))
            self._write_data(X[test_idx], y[test_idx], os.path.join(root, "yeast.test"))

        if train:
            data_path = os.path.join(root, "yeast.train")
        else:
            data_path = os.path.join(root, "yeast.test")

        X, y = self._load_data(data_path)
        X = torch.from_numpy(X).type(torch.FloatTensor)
        y = torch.from_numpy(y).type(torch.IntTensor)
        return X,y