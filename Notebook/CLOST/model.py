from .imports import *
from .utils import *
from .volumes import create_normalized_volume, denormalize_volume


def create_data_dict(city, X_name, y_name):

  if (city != 'NY') & (city != 'BJ'):

    return(print('You can insert NY or BJ as city'))

  else:

    X, y = {}, {}
    for name in X_name:
      tmp = np.load('../data/' + city + '/volumes/' + name + '.npy')
      shape = tmp.shape[1] * tmp.shape[2]
      if city == 'NY':
        X[name] = tmp.reshape((len(tmp), shape, 16, 8 , 1))
      elif city == 'BJ':
        X[name] = tmp.reshape((len(tmp), shape, 32, 32 , 1))

    for name in y_name:
      tmp = np.load('../data/' + city + '/volumes/' + name + '.npy')
      if city == 'NY':
        y[name] = tmp.reshape((len(tmp), 2, 16, 8))
      elif city == 'BJ':
        y[name] = tmp.reshape((len(tmp), 2, 32, 32))
    
    return X, y

	
def create_train_test(city, X, y, external_data, test_days):

  # Funzione che divide training set da test set.
  # Input: - X: Volume contenente i dati da passare in input al modello
  #        - y: Volume contenente i dati da prevedere
  #        - external_data: Volume con le informazioni esterne (meteo, festivitĂÂ ,...)
  #        - test_days: numero di giorni del test set

  if (city != 'NY') & (city != 'BJ'):

    return(print('You can insert NY or BJ as city'))

  else:
    external_data = external_data[-len(X):]
    if city == 'NY':
      hour = 24
    elif city == 'BJ':
      hour = 48
    X_train = X[:- test_days * hour]
    X_test = X[- test_days * hour:]
    y_train = y[:- test_days * hour]
    y_test = y[- test_days * hour:]
    external_data_train = external_data[:- test_days * hour]
    external_data_test = external_data[- test_days * hour:]
    return X_train, X_test, y_train, y_test, external_data_train, external_data_test
	
	
def CLoST3D(city, X, y,  external_data, test_days,
            conv_filt = 64, kernel_sz = (2, 3, 3), lr = 0.001, normalize = False,
            epochs = 10, mask = np.empty(0),
            lstm = None, lstm_number = 0,
            add_external_info = False):
  
  # Funzione utilizzata per trainare il modello. Vengono divisi trainig e test set, aggiunte le informazioni esterne e creata la rete.
  # Infine viene addrestato il modello e salvati i risultati nel file './drive/My Drive/Smart Mobility Prediction/dataset/model_runs.csv'
  # Input: 
  #     - X: Dict. Dizionario contenente tutti i possibili diversi Volumi di input
  #     - name_x: Str. Nome della chiave del dizionario X su cui si vuole addestrare il modello
  #     - y: X: Dict. Dizionario contenente tutti i possibili diversi output
  #     - name_y: Str. Nome della chiave del dizionario y su cui si vuole addestrare il modello
  #     - external_data: np.array. Volume con le informazioni esterne (meteo, festivitÃ ,...)
  #     - test_days: int. Numero di giorni del test set
  #     - epochs: int. Numero di epoche su cui addestrare il modello. Default = 10
  #     - mask: np.array. Filtro che viene applicato ai dati in output al modello. Se non viene passato, non viene applicato nessun filtro
  #     - lstm: int. Parametro da passare al layer LSTM. Se uguale a None, non viene aggiunto lo strato di LSTM.
  #     - add_external_info: bool. Parametro per inserire o meno le informazioni esterne.

  
  if ((lstm == None) & (lstm_number > 0)) | ((lstm != None) & (lstm_number == 0)):
    
    return(print('If you want to add LSTM layers you have to initialize lstm and lstm_number parameters'))
  
  else:


    if normalize:
      print('Starting normalization...')
      vol_min, vol_max, X = create_normalized_volume(X)
      _, _, y = create_normalized_volume(y)
      print('Normalization OK.')

    X_train, X_test, y_train, y_test, ext_train, ext_test = create_train_test(city, X, y, external_data, test_days)
    X_train = np.reshape(X_train, (X_train.shape[0], int(X_train.shape[1]/2),X_train.shape[2], X_train.shape[3], 2))
    X_test = np.reshape(X_test, (X_test.shape[0], int(X_test.shape[1]/2),X_test.shape[2], X_test.shape[3], 2))

    main_inputs, train_data, test_data = [], [], []

    start = Input(shape= (X_train.shape[1], X_train.shape[2] , X_train.shape[3], 2))

    main_inputs.append(start)
    main_output = main_inputs[0]
    train_data.append(X_train)
    test_data.append(X_test)


    x = Conv3D(conv_filt / 2, kernel_size = kernel_sz, activation='relu')(main_output)
    x = MaxPooling3D(pool_size=(1, 2, 2))(x)
    x = Dropout(0.25)(x)
    x = Conv3D(conv_filt, kernel_size = kernel_sz, activation='relu', padding = 'same')(x)
    x = MaxPooling3D(pool_size=(1, 2, 2))(x)
    if city == 'BJ':
      x = Dropout(0.25)(x)
      x = Conv3D(conv_filt, kernel_size = kernel_sz, activation='relu', padding = 'same')(x)
      x = MaxPooling3D(pool_size=(1, 2, 2))(x)
    x = Flatten()(x)
    x = Dense(128,  activation = 'relu') (x)
    if lstm != None:
      x = Reshape((x.shape[1], 1))(x)
      for num in range(lstm_number):
        if city == 'BJ':
          x = LSTM(int(lstm/(num+1)), return_sequences=True)(x)
        elif city == 'NY':
          x = LSTM(int(lstm), return_sequences=True)(x)
    x = Flatten()(x)
    if add_external_info:
      external_input = Input(shape=ext_train.shape[1:])
      main_inputs.append(external_input)
      train_data.append(ext_train)
      test_data.append(ext_test)
      x_ext = Dense(units=10, activation='relu')(external_input)
      x_ext = Dense(units=reduce(lambda e1, e2: e1*e2, y_train.shape[1:]), activation='relu')(x_ext)
      x = Flatten()(x)
      x = Concatenate(axis = -1)([x, x_ext])
    x = Dense(reduce(lambda e1, e2: e1*e2, y_train.shape[1:]))(x)
    x = Reshape(y_train.shape[1:])(x)
    x = Activation(swish)(x)
    if mask.shape[0] != 0:
      x = Lambda(lambda el: el * mask)(x) 
    model = Model(main_inputs, x)

    model.compile(loss = root_mean_squared_error, optimizer='adam', metrics = [root_mean_squared_error])
    K.set_value(model.optimizer.lr, lr)

    model.fit(x = train_data, y = y_train, batch_size= 64,verbose = 0, epochs=epochs)

    predictions = model.predict(test_data)

    if normalize:
      print('Starting denormalization...')
      inflow_real = denormalize_volume(np.array([el[0] for el in y_test]), vol_min, vol_max)
      outflow_real = denormalize_volume(np.array([el[1] for el in y_test]), vol_min, vol_max)

      inflow_pred = denormalize_volume(np.array([el[0] for el in predictions]), vol_min, vol_max)
      outflow_pred = denormalize_volume(np.array([el[1] for el in predictions]), vol_min, vol_max)

      predictions = denormalize_volume(predictions, vol_min, vol_max)
      y_test = denormalize_volume(y_test, vol_min, vol_max)
      rmse = sqrt(mean_squared_error(y_test, predictions))
    else:
      rmse = sqrt(mean_squared_error(y_test.flatten(), predictions.flatten()))
      inflow_real = np.array([el[0] for el in y_test]).flatten()
      outflow_real = np.array([el[1] for el in y_test]).flatten()

      inflow_pred = np.array([el[0] for el in predictions]).flatten()
      outflow_pred = np.array([el[1] for el in predictions]).flatten()
    
    rmse_inflow = sqrt(mean_squared_error(inflow_real, inflow_pred))
    rmse_outflow = sqrt(mean_squared_error(outflow_real, outflow_pred))
    print('RMSE: {}, RMSE inflow: {}, RMSE outflow: {}'.format(rmse, rmse_inflow, rmse_outflow))

    
    return rmse, predictions, model